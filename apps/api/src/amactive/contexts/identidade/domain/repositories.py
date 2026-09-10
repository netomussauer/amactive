"""Portas (Protocols) do contexto Identidade & Acesso."""

from __future__ import annotations

from typing import Protocol

from amactive.contexts.identidade.domain.entities import Usuario


class UsuarioRepository(Protocol):
    async def buscar_por_email(self, email: str) -> Usuario | None: ...
