"""Casos de uso de Fornecedor (Command/Query)."""

from __future__ import annotations

from uuid import UUID

from amactive.contexts.cadastros.domain.entities import Fornecedor
from amactive.contexts.cadastros.domain.exceptions import FornecedorNaoEncontrado
from amactive.contexts.cadastros.domain.repositories import FornecedorRepository


class CriarFornecedorCommand:
    def __init__(self, repository: FornecedorRepository) -> None:
        self._repository = repository

    async def executar(self, **campos: object) -> Fornecedor:
        return await self._repository.criar(**campos)


class ListarFornecedoresQuery:
    def __init__(self, repository: FornecedorRepository) -> None:
        self._repository = repository

    async def executar(
        self, *, page: int, per_page: int, busca: str | None
    ) -> tuple[list[Fornecedor], int]:
        return await self._repository.listar(page=page, per_page=per_page, busca=busca)


class ObterFornecedorQuery:
    def __init__(self, repository: FornecedorRepository) -> None:
        self._repository = repository

    async def executar(self, fornecedor_id: UUID) -> Fornecedor:
        fornecedor = await self._repository.buscar_por_id(fornecedor_id)
        if fornecedor is None:
            raise FornecedorNaoEncontrado(f"Fornecedor {fornecedor_id} não encontrado.")
        return fornecedor


class AtualizarFornecedorCommand:
    def __init__(self, repository: FornecedorRepository) -> None:
        self._repository = repository

    async def executar(self, fornecedor_id: UUID, **campos: object) -> Fornecedor:
        fornecedor = await self._repository.atualizar(fornecedor_id, **campos)
        if fornecedor is None:
            raise FornecedorNaoEncontrado(f"Fornecedor {fornecedor_id} não encontrado.")
        return fornecedor


class InativarFornecedorCommand:
    def __init__(self, repository: FornecedorRepository) -> None:
        self._repository = repository

    async def executar(self, fornecedor_id: UUID) -> None:
        inativado = await self._repository.inativar(fornecedor_id)
        if not inativado:
            raise FornecedorNaoEncontrado(f"Fornecedor {fornecedor_id} não encontrado.")
