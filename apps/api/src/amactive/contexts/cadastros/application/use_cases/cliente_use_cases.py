"""Casos de uso de Cliente (Command/Query)."""

from __future__ import annotations

from uuid import UUID

from amactive.contexts.cadastros.domain.entities import Cliente
from amactive.contexts.cadastros.domain.exceptions import ClienteNaoEncontrado
from amactive.contexts.cadastros.domain.repositories import ClienteRepository


class CriarClienteCommand:
    def __init__(self, repository: ClienteRepository) -> None:
        self._repository = repository

    async def executar(self, **campos: object) -> Cliente:
        return await self._repository.criar(**campos)


class ListarClientesQuery:
    def __init__(self, repository: ClienteRepository) -> None:
        self._repository = repository

    async def executar(
        self, *, page: int, per_page: int, busca: str | None
    ) -> tuple[list[Cliente], int]:
        return await self._repository.listar(page=page, per_page=per_page, busca=busca)


class ObterClienteQuery:
    def __init__(self, repository: ClienteRepository) -> None:
        self._repository = repository

    async def executar(self, cliente_id: UUID) -> Cliente:
        cliente = await self._repository.buscar_por_id(cliente_id)
        if cliente is None:
            raise ClienteNaoEncontrado(f"Cliente {cliente_id} não encontrado.")
        return cliente


class AtualizarClienteCommand:
    def __init__(self, repository: ClienteRepository) -> None:
        self._repository = repository

    async def executar(self, cliente_id: UUID, **campos: object) -> Cliente:
        cliente = await self._repository.atualizar(cliente_id, **campos)
        if cliente is None:
            raise ClienteNaoEncontrado(f"Cliente {cliente_id} não encontrado.")
        return cliente


class InativarClienteCommand:
    def __init__(self, repository: ClienteRepository) -> None:
        self._repository = repository

    async def executar(self, cliente_id: UUID) -> None:
        inativado = await self._repository.inativar(cliente_id)
        if not inativado:
            raise ClienteNaoEncontrado(f"Cliente {cliente_id} não encontrado.")
