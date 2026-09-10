"""Queries de leitura de Pedido."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from amactive.contexts.vendas.domain.entities import Pedido, StatusPedido
from amactive.contexts.vendas.domain.exceptions import PedidoNaoEncontrado
from amactive.contexts.vendas.domain.repositories import PedidoRepository


class ListarPedidosQuery:
    def __init__(self, repository: PedidoRepository) -> None:
        self._repository = repository

    async def executar(
        self,
        *,
        page: int,
        per_page: int,
        status: StatusPedido | None,
        cliente_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
    ) -> tuple[list[Pedido], int]:
        return await self._repository.listar(
            page=page,
            per_page=per_page,
            status=status,
            cliente_id=cliente_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )


class ObterPedidoQuery:
    def __init__(self, repository: PedidoRepository) -> None:
        self._repository = repository

    async def executar(self, pedido_id: UUID) -> Pedido:
        pedido = await self._repository.buscar_por_id(pedido_id)
        if pedido is None:
            raise PedidoNaoEncontrado(f"Pedido {pedido_id} não encontrado.")
        return pedido
