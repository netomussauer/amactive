"""Command: criar e confirmar uma venda em uma única transação atômica.

Regra crítica de negócio (ver docs/data-model.md § Estratégia de
Concorrência — Baixa de Estoque e docs/openapi.yaml `POST /pedidos`):
  1. O pedido, seus itens e pagamentos são persistidos e a baixa de estoque
     de cada item é feita via `EstoquePort.registrar_saida_venda` — que por
     sua vez sempre faz `INSERT INTO movimentacao_estoque` (nunca `UPDATE
     estoque` diretamente). O trigger de banco aplica o delta atomicamente.
  2. Os itens são processados em ordem determinística por `variante_id`
     (não a ordem em que vieram no request) para evitar deadlock entre
     pedidos concorrentes que compartilham SKUs.
  3. Se qualquer item não tiver saldo suficiente, a exceção de domínio
     propagada pelo `EstoquePort` já disparou um `ROLLBACK` da transação
     inteira (incluindo o pedido e os itens já inseridos) — nenhuma alteração
     parcial é persistida.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.domain.entities import OrigemCanalPedido, Pedido, StatusPedido
from amactive.contexts.vendas.domain.exceptions import (
    PagamentosNaoConferem,
    VarianteDeVendaInvalida,
)
from amactive.contexts.vendas.domain.repositories import CatalogoPort, EstoquePort, PedidoRepository


class CriarPedidoUseCase:
    def __init__(
        self,
        pedido_repository: PedidoRepository,
        catalogo_port: CatalogoPort,
        estoque_port: EstoquePort,
    ) -> None:
        self._pedidos = pedido_repository
        self._catalogo = catalogo_port
        self._estoque = estoque_port

    async def executar(
        self,
        *,
        cliente_id: UUID | None,
        desconto: Decimal,
        observacao: str | None,
        itens: list[ItemPedidoInput],
        pagamentos: list[PagamentoInput],
        usuario_id: UUID,
        # Novos, ambos com default — 100% retrocompatível com o endpoint do
        # PDV (docs/design-integracao-nuvemshop.md §3.1). O worker de webhook
        # da Nuvemshop (fora do escopo deste módulo) é quem passa valores
        # diferentes do default.
        origem_canal: OrigemCanalPedido = OrigemCanalPedido.PDV,
        pedido_externo_id: str | None = None,
    ) -> Pedido:
        itens_processados: list[dict] = []
        subtotal_pedido = Decimal("0.00")

        for item in itens:
            variante = await self._catalogo.buscar_variante_para_venda(item.variante_id)
            if variante is None or not variante.ativo:
                raise VarianteDeVendaInvalida(
                    f"Variante {item.variante_id} não encontrada ou inativa para venda."
                )
            subtotal_item = (variante.preco_venda * item.quantidade) - item.desconto_item
            if subtotal_item < 0:
                raise VarianteDeVendaInvalida(
                    f"Desconto do item da variante {variante.sku} excede o valor do item."
                )
            subtotal_pedido += subtotal_item
            itens_processados.append(
                {
                    "variante_id": variante.id,
                    "sku": variante.sku,
                    "quantidade": item.quantidade,
                    "preco_unitario": variante.preco_venda,
                    "desconto_item": item.desconto_item,
                    "subtotal": subtotal_item,
                }
            )

        valor_total = subtotal_pedido - desconto
        if valor_total < 0:
            raise VarianteDeVendaInvalida("Desconto do pedido excede o subtotal calculado.")

        soma_pagamentos = sum((p.valor for p in pagamentos), Decimal("0.00"))
        if soma_pagamentos != valor_total:
            raise PagamentosNaoConferem(
                f"Soma dos pagamentos ({soma_pagamentos}) difere do valor total do "
                f"pedido ({valor_total})."
            )

        numero = await self._pedidos.proximo_numero()
        pedido = await self._pedidos.criar(
            numero=numero,
            cliente_id=cliente_id,
            usuario_id=usuario_id,
            status=StatusPedido.CONFIRMADO,
            subtotal=subtotal_pedido,
            desconto=desconto,
            valor_total=valor_total,
            observacao=observacao,
            confirmado_em=datetime.now(UTC),
            origem_canal=origem_canal,
            pedido_externo_id=pedido_externo_id,
            itens=itens_processados,
            pagamentos=[
                {"forma_pagamento": p.forma_pagamento, "valor": p.valor} for p in pagamentos
            ],
        )

        # Ordenação determinística por variante_id — ver docstring do módulo.
        for item_processado in sorted(itens_processados, key=lambda i: str(i["variante_id"])):
            await self._estoque.registrar_saida_venda(
                variante_id=item_processado["variante_id"],
                quantidade=item_processado["quantidade"],
                pedido_id=pedido.id,
                usuario_id=usuario_id,
            )

        return pedido
