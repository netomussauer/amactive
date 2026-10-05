"""Command: checkout da vitrine online — cria um pedido PENDENTE e RESERVA o estoque.

Diferente de `CriarPedidoUseCase` (PDV/canais), aqui NÃO há pagamento nem baixa
de estoque: o cliente final só pediu, e a equipe fecha o pagamento depois via
WhatsApp (ver `ConfirmarPagamentoVitrineUseCase`). Para não vender a mesma
peça duas vezes enquanto o pagamento não chega, as unidades são RESERVADAS
por um prazo (`prazo_reserva`). Regras:

  1. Preço e desconto são recalculados aqui, a partir do catálogo — o cliente
     nunca envia valor. O desconto promocional do produto
     (`desconto_percentual`) é aplicado como `desconto_item`, pelo mesmo
     mecanismo já usado pelo PDV.
  2. Disponibilidade = saldo físico - reservas ativas. Antes de contar, a
     linha de `estoque` é travada (`saldo_bloqueado`, FOR UPDATE), em ordem
     determinística por `variante_id` — dois checkouts concorrentes da última
     unidade não passam os dois.
  3. Reserva vencida: antes de qualquer checkout, os pedidos com reserva
     expirada são cancelados e suas reservas removidas (expiração preguiçosa,
     sem worker dedicado). Pedido vencido deixa de contar no saldo mesmo antes
     dessa limpeza, porque a disponibilidade filtra por `reservado_ate > agora`.
  4. Sem operador: `usuario_id` fica nulo (migrations/000008).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

from amactive.contexts.vendas.domain.entities import OrigemCanalPedido, Pedido, StatusPedido
from amactive.contexts.vendas.domain.exceptions import (
    ItensVitrineInvalidos,
    VarianteDeVendaInvalida,
)
from amactive.contexts.vendas.domain.repositories import (
    CatalogoPort,
    ClientePort,
    EstoquePort,
    PedidoRepository,
    ReservaEstoquePort,
)
from amactive.shared_kernel.exceptions import ErroDeValidacao, EstoqueInsuficiente
from amactive.shared_kernel.money import aplicar_desconto_percentual

PRAZO_RESERVA_PADRAO = timedelta(hours=24)

_TELEFONE_MIN_DIGITOS = 10
_TELEFONE_MAX_DIGITOS = 13


@dataclass(frozen=True)
class ItemVitrineInput:
    variante_id: UUID
    quantidade: int


class CriarPedidoVitrineUseCase:
    def __init__(
        self,
        pedido_repository: PedidoRepository,
        catalogo_port: CatalogoPort,
        estoque_port: EstoquePort,
        cliente_port: ClientePort,
        reserva_port: ReservaEstoquePort,
        *,
        prazo_reserva: timedelta = PRAZO_RESERVA_PADRAO,
    ) -> None:
        self._pedidos = pedido_repository
        self._catalogo = catalogo_port
        self._estoque = estoque_port
        self._clientes = cliente_port
        self._reservas = reserva_port
        self._prazo_reserva = prazo_reserva

    async def executar(
        self,
        *,
        cliente_nome: str,
        cliente_telefone: str,
        observacao: str | None,
        itens: list[ItemVitrineInput],
        agora: datetime,
    ) -> Pedido:
        if not itens:
            raise ErroDeValidacao("O carrinho está vazio.")
        ids = [item.variante_id for item in itens]
        if len(set(ids)) != len(ids):
            raise ItensVitrineInvalidos(
                "A mesma variante aparece mais de uma vez no carrinho. "
                "Some as quantidades em uma única linha."
            )
        telefone = _normalizar_telefone(cliente_telefone)

        await self._cancelar_reservas_vencidas(agora)

        itens_processados: list[dict] = []
        subtotal = Decimal("0.00")
        for item in sorted(itens, key=lambda i: str(i.variante_id)):
            variante = await self._catalogo.buscar_variante_para_venda(item.variante_id)
            if variante is None or not variante.ativo:
                raise VarianteDeVendaInvalida(
                    f"Variante {item.variante_id} não encontrada ou indisponível para venda."
                )

            preco_efetivo = variante.preco_venda
            if variante.desconto_percentual is not None:
                preco_efetivo = aplicar_desconto_percentual(
                    variante.preco_venda, variante.desconto_percentual
                )
            subtotal_bruto = variante.preco_venda * item.quantidade
            subtotal_item = preco_efetivo * item.quantidade

            saldo = await self._estoque.saldo_bloqueado(variante.id)
            reservado = await self._reservas.quantidade_reservada_ativa(variante.id, agora=agora)
            disponivel = saldo - reservado
            if item.quantidade > disponivel:
                raise EstoqueInsuficiente(
                    f"Produto '{variante.produto_nome}' ({variante.sku}): restam "
                    f"{max(disponivel, 0)} unidade(s) disponível(is)."
                )

            subtotal += subtotal_item
            itens_processados.append(
                {
                    "variante_id": variante.id,
                    "sku": variante.sku,
                    "quantidade": item.quantidade,
                    "preco_unitario": variante.preco_venda,
                    "desconto_item": subtotal_bruto - subtotal_item,
                    "subtotal": subtotal_item,
                }
            )

        cliente_id = await self._clientes.obter_ou_criar_por_telefone(
            nome=cliente_nome, telefone=telefone
        )
        numero = await self._pedidos.proximo_numero()
        pedido = await self._pedidos.criar(
            numero=numero,
            cliente_id=cliente_id,
            usuario_id=None,
            status=StatusPedido.PENDENTE,
            subtotal=subtotal,
            desconto=Decimal("0.00"),
            valor_total=subtotal,
            observacao=observacao,
            confirmado_em=None,
            origem_canal=OrigemCanalPedido.VITRINE,
            pedido_externo_id=None,
            itens=itens_processados,
            pagamentos=[],
            reservado_ate=agora + self._prazo_reserva,
        )
        for item_processado in itens_processados:
            await self._reservas.registrar(
                pedido_id=pedido.id,
                variante_id=item_processado["variante_id"],
                quantidade=item_processado["quantidade"],
            )
        return pedido

    async def _cancelar_reservas_vencidas(self, agora: datetime) -> None:
        for pedido_id in await self._reservas.pedidos_com_reserva_vencida(agora=agora):
            await self._reservas.liberar_do_pedido(pedido_id)
            await self._pedidos.atualizar_status(
                pedido_id, status=StatusPedido.CANCELADO, timestamp=agora
            )


def _normalizar_telefone(telefone: str) -> str:
    digitos = re.sub(r"\D", "", telefone)
    if not _TELEFONE_MIN_DIGITOS <= len(digitos) <= _TELEFONE_MAX_DIGITOS:
        raise ErroDeValidacao("Informe um telefone válido com DDD (ex.: 11 99999-9999).")
    return digitos
