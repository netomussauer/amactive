"""Command — usado pelo worker (`run_worker.py`, ainda não implementado —
ver docs/design-integracao-nuvemshop.md §9 passo 7).

Implementa o fluxo completo de design §5.3: busca o pedido completo via
`NuvemshopClientPort` (o payload do webhook não traz os itens), resolve o
cliente via `ClienteIntegracaoPort`, resolve cada item via
`MapeamentoVarianteRepository` (tudo ou nada — qualquer item sem mapeamento
manda o evento inteiro para `CONFLITO_MANUAL`, nenhum pedido parcial é
criado) e confirma o pedido via `PedidoIntegracaoPort`, tratando os três
desfechos possíveis do diagrama de sequência (§5.3):

- sucesso -> `WebhookEventoRepository.marcar_processado`
- `PedidoExternoJaProcessado` -> `marcar_processado` (idempotente, não é erro)
- `SaldoDeEstoqueInsuficiente` -> `marcar_conflito_manual` (log ERROR — maior
  severidade de negócio: pedido já pago na Nuvemshop, não pôde ser criado)
- erro transitório (rede/5xx da Nuvemshop, deadlock) -> `marcar_erro`
  (`tentativas += 1`, reprocessado no próximo tick pelo worker)
"""

from __future__ import annotations

from decimal import Decimal

import structlog

from amactive.contexts.catalogo_estoque.domain.exceptions import SaldoDeEstoqueInsuficiente
from amactive.contexts.integracao_canais.domain.entities import WebhookEvento
from amactive.contexts.integracao_canais.domain.exceptions import (
    NuvemshopIndisponivel,
    PedidoExternoJaProcessado,
)
from amactive.contexts.integracao_canais.domain.repositories import (
    ClienteIntegracaoPort,
    MapeamentoVarianteRepository,
    NuvemshopClientPort,
    PedidoIntegracaoPort,
    WebhookEventoRepository,
)
from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.domain.entities import FormaPagamento, OrigemCanalPedido
from amactive.contexts.vendas.domain.exceptions import PagamentosNaoConferem
from amactive.shared_kernel.exceptions import ConflitoTransacional

# Único tipo de evento assinado na Fase 1 (avaliação §6) — `order/cancelled`
# e `product/updated` ficam para a Fase 2. `run_worker.py` (passo 7) é quem
# decide quais eventos passam por este use case; ele mesmo não filtra por
# `tipo_evento` porque, na Fase 1, a Nuvemshop só é configurada para
# entregar `order/paid` (fora do escopo Python, ver design §9 item 9).
TIPO_EVENTO_PEDIDO_PAGO = "order/paid"

# Log estruturado a cada transição de status de `webhook_evento` (design
# §8) — sempre incluindo `evento_externo_id`, nunca o payload bruto (pode
# conter dados pessoais do comprador) nem qualquer token/secret.
_logger = structlog.get_logger(__name__)


class ProcessarWebhookPedidoUseCase:
    """Ver docstring do módulo."""

    def __init__(
        self,
        *,
        nuvemshop_client: NuvemshopClientPort,
        cliente_integracao: ClienteIntegracaoPort,
        mapeamento_variante_repository: MapeamentoVarianteRepository,
        pedido_integracao: PedidoIntegracaoPort,
        webhook_evento_repository: WebhookEventoRepository,
    ) -> None:
        self._nuvemshop = nuvemshop_client
        self._clientes = cliente_integracao
        self._mapeamentos = mapeamento_variante_repository
        self._pedidos = pedido_integracao
        self._webhook_eventos = webhook_evento_repository

    async def executar(self, evento: WebhookEvento) -> None:
        try:
            pedido_externo = await self._nuvemshop.buscar_pedido(evento.id_recurso_externo)
        except NuvemshopIndisponivel as exc:
            await self._webhook_eventos.marcar_erro(evento.id, detalhe=str(exc))
            _logger.warning(
                "webhook_evento.erro",
                evento_externo_id=evento.evento_externo_id,
                motivo="nuvemshop_indisponivel_ao_buscar_pedido",
                detalhe=str(exc),
            )
            return

        cliente_id = await self._clientes.resolver_ou_criar_por_email(
            email=pedido_externo.cliente_email,
            nome=pedido_externo.cliente_nome,
            cpf_cnpj=pedido_externo.cliente_cpf_cnpj,
            telefone=pedido_externo.cliente_telefone,
            endereco=pedido_externo.cliente_endereco,
            cliente_externo_id=pedido_externo.cliente_externo_id,
        )

        itens: list[ItemPedidoInput] = []
        for item_externo in pedido_externo.itens:
            mapeamento = await self._mapeamentos.buscar_por_variante_externo(
                canal=evento.canal, variante_externo_id=item_externo.variante_externo_id
            )
            if mapeamento is None:
                # Tudo ou nada (mesma filosofia de `CriarPedidoUseCase`) —
                # qualquer item sem mapeamento cancela o evento inteiro,
                # nunca cria um pedido parcial (design §5.3 passo 3).
                detalhe = (
                    f"Item sem MapeamentoVarianteCanal: produto_externo_id="
                    f"{item_externo.produto_externo_id}, variante_externo_id="
                    f"{item_externo.variante_externo_id}."
                )
                await self._webhook_eventos.marcar_conflito_manual(evento.id, detalhe=detalhe)
                _logger.warning(
                    "webhook_evento.conflito_manual",
                    evento_externo_id=evento.evento_externo_id,
                    motivo="variante_nao_mapeada",
                    detalhe=detalhe,
                )
                return
            itens.append(
                ItemPedidoInput(
                    variante_id=mapeamento.variante_id,
                    quantidade=item_externo.quantidade,
                    # A Nuvemshop já aplica seus próprios descontos antes de
                    # informar `total` (mapeado para `valor_total` — ver
                    # `mappers.py`); não há desconto por item do MVP a
                    # replicar aqui (design §3.1).
                    desconto_item=Decimal("0.00"),
                )
            )

        pagamentos = [
            PagamentoInput(
                forma_pagamento=FormaPagamento.NUVEMSHOP, valor=pedido_externo.valor_total
            )
        ]

        try:
            await self._pedidos.confirmar_pedido_externo(
                cliente_id=cliente_id,
                itens=itens,
                pagamentos=pagamentos,
                origem_canal=OrigemCanalPedido.NUVEMSHOP,
                pedido_externo_id=pedido_externo.pedido_externo_id,
            )
        except PedidoExternoJaProcessado:
            # Idempotente — o pedido já existia (ex.: reconciliação e
            # webhook concorrentes). Não é erro (design §5.3/§5.2).
            await self._webhook_eventos.marcar_processado(evento.id)
            _logger.info(
                "webhook_evento.processado",
                evento_externo_id=evento.evento_externo_id,
                motivo="pedido_externo_ja_processado_idempotente",
            )
            return
        except SaldoDeEstoqueInsuficiente as exc:
            # Maior severidade de negócio: o pedido já foi pago na
            # Nuvemshop e não pôde ser criado no AMACTIVE (design §5.4/§9).
            await self._webhook_eventos.marcar_conflito_manual(evento.id, detalhe=str(exc))
            # Log ERROR dedicado (design §8, além da transição de status
            # acima) — maior severidade de negócio: pedido já pago na
            # Nuvemshop, não pôde ser criado no AMACTIVE.
            _logger.error(
                "webhook_evento.conflito_manual",
                evento_externo_id=evento.evento_externo_id,
                motivo="saldo_estoque_insuficiente",
                detalhe=str(exc),
            )
            return
        except PagamentosNaoConferem as exc:
            # `CriarPedidoUseCase` exige soma dos pagamentos == subtotal
            # calculado a partir do `preco_venda` ATUAL do AMACTIVE — mas o
            # `valor_total` de um pedido Nuvemshop pode legitimamente
            # divergir disso (frete incluso no total, cupom aplicado do lado
            # da Nuvemshop, arredondamento, ou o preço ter mudado no
            # AMACTIVE entre a última publicação de catálogo e esta compra).
            # Não é um bug de payload nem algo que se corrija reprocessando
            # — trata-se como conflito manual (mesma severidade de estoque
            # insuficiente: pedido já pago na Nuvemshop, precisa de revisão
            # humana), nunca como erro transitório.
            await self._webhook_eventos.marcar_conflito_manual(evento.id, detalhe=str(exc))
            _logger.warning(
                "webhook_evento.conflito_manual",
                evento_externo_id=evento.evento_externo_id,
                motivo="pagamentos_nao_conferem",
                detalhe=str(exc),
            )
            return
        except ConflitoTransacional as exc:
            # Deadlock genuíno detectado pelo Postgres — erro transitório,
            # reprocessado no próximo tick do worker (design §4.3/§5.3).
            await self._webhook_eventos.marcar_erro(evento.id, detalhe=str(exc))
            _logger.warning(
                "webhook_evento.erro",
                evento_externo_id=evento.evento_externo_id,
                motivo="conflito_transacional",
                detalhe=str(exc),
            )
            return

        await self._webhook_eventos.marcar_processado(evento.id)
        _logger.info(
            "webhook_evento.processado",
            evento_externo_id=evento.evento_externo_id,
            pedido_externo_id=pedido_externo.pedido_externo_id,
        )
