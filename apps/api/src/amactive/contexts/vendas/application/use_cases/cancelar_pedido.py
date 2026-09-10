"""Command: cancelar um pedido, estornando o estoque se já estava CONFIRMADO."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from amactive.contexts.vendas.domain.entities import Pedido, StatusPedido
from amactive.contexts.vendas.domain.exceptions import PedidoJaCancelado, PedidoNaoEncontrado
from amactive.contexts.vendas.domain.repositories import EstoquePort, PedidoRepository


class CancelarPedidoUseCase:
    def __init__(self, pedido_repository: PedidoRepository, estoque_port: EstoquePort) -> None:
        self._pedidos = pedido_repository
        self._estoque = estoque_port

    async def executar(self, pedido_id: UUID, *, usuario_id: UUID) -> Pedido:
        pedido = await self._pedidos.buscar_por_id(pedido_id)
        if pedido is None:
            raise PedidoNaoEncontrado(f"Pedido {pedido_id} não encontrado.")
        if pedido.status == StatusPedido.CANCELADO:
            raise PedidoJaCancelado(f"Pedido {pedido.numero} já está cancelado.")

        if pedido.status == StatusPedido.CONFIRMADO:
            # Estorno — mesmo mecanismo (INSERT em movimentacao_estoque,
            # nunca UPDATE em estoque), ordenado por variante_id.
            for item in sorted(pedido.itens, key=lambda i: str(i.variante_id)):
                await self._estoque.registrar_entrada_devolucao(
                    variante_id=item.variante_id,
                    quantidade=item.quantidade,
                    pedido_id=pedido.id,
                    usuario_id=usuario_id,
                )

        agora = datetime.now(UTC)
        await self._pedidos.atualizar_status(
            pedido_id, status=StatusPedido.CANCELADO, timestamp=agora
        )

        pedido_atualizado = await self._pedidos.buscar_por_id(pedido_id)
        assert pedido_atualizado is not None  # já validamos a existência acima
        return pedido_atualizado
