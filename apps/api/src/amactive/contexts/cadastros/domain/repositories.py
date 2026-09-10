"""Portas (Protocols) do contexto Cadastros."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from amactive.contexts.cadastros.domain.entities import Cliente, Fornecedor


class ClienteRepository(Protocol):
    async def criar(self, **campos: object) -> Cliente: ...

    async def listar(
        self, *, page: int, per_page: int, busca: str | None
    ) -> tuple[list[Cliente], int]: ...

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None: ...

    async def atualizar(self, cliente_id: UUID, **campos: object) -> Cliente | None: ...

    async def inativar(self, cliente_id: UUID) -> bool: ...


class FornecedorRepository(Protocol):
    async def criar(self, **campos: object) -> Fornecedor: ...

    async def listar(
        self, *, page: int, per_page: int, busca: str | None
    ) -> tuple[list[Fornecedor], int]: ...

    async def buscar_por_id(self, fornecedor_id: UUID) -> Fornecedor | None: ...

    async def atualizar(self, fornecedor_id: UUID, **campos: object) -> Fornecedor | None: ...

    async def inativar(self, fornecedor_id: UUID) -> bool: ...
