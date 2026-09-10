"""Implementação concreta de `UsuarioRepository` (domain/repositories.py)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.identidade.domain.entities import PapelUsuario, Usuario
from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel


class SqlAlchemyUsuarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def buscar_por_email(self, email: str) -> Usuario | None:
        resultado = await self._session.execute(
            select(UsuarioModel).where(UsuarioModel.email == email)
        )
        modelo = resultado.scalar_one_or_none()
        if modelo is None:
            return None
        return Usuario(
            id=modelo.id,
            nome=modelo.nome,
            email=modelo.email,
            senha_hash=modelo.senha_hash,
            papel=PapelUsuario(modelo.papel),
            ativo=modelo.ativo,
        )
