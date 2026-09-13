"""Portas (Protocols) do contexto Identidade & Acesso."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from amactive.contexts.identidade.domain.entities import PapelUsuario, Usuario


class UsuarioRepository(Protocol):
    async def buscar_por_email(self, email: str) -> Usuario | None: ...

    async def criar(
        self, *, nome: str, email: str, senha_hash: str, papel: PapelUsuario
    ) -> Usuario: ...

    async def listar(self, *, page: int, per_page: int) -> tuple[list[Usuario], int]: ...

    async def buscar_por_id(self, usuario_id: UUID) -> Usuario | None: ...

    async def atualizar(
        self, usuario_id: UUID, *, nome: str, papel: PapelUsuario, ativo: bool
    ) -> Usuario | None: ...

    async def atualizar_senha(self, usuario_id: UUID, senha_hash: str) -> bool: ...

    async def inativar(self, usuario_id: UUID) -> bool: ...

    async def contar_admins_ativos(self) -> int:
        """Conta usuários com `papel=ADMIN` e `ativo=true` — usado pela
        salvaguarda do "último ADMIN ativo" (ver domain/exceptions.UltimoAdminAtivo)."""
        ...
