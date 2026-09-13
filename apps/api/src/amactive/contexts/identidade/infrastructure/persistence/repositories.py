"""Implementação concreta de `UsuarioRepository` (domain/repositories.py)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.identidade.domain.entities import PapelUsuario, Usuario
from amactive.contexts.identidade.domain.exceptions import EmailDuplicado
from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel
from amactive.shared_kernel.pagination import offset_limit


def _now() -> datetime:
    return datetime.now(UTC)


class SqlAlchemyUsuarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def buscar_por_email(self, email: str) -> Usuario | None:
        resultado = await self._session.execute(
            select(UsuarioModel).where(UsuarioModel.email == email)
        )
        modelo = resultado.scalar_one_or_none()
        return _usuario_para_entidade(modelo) if modelo else None

    async def criar(
        self, *, nome: str, email: str, senha_hash: str, papel: PapelUsuario
    ) -> Usuario:
        modelo = UsuarioModel(
            id=uuid.uuid4(),
            nome=nome,
            email=email,
            senha_hash=senha_hash,
            papel=papel.value,
            ativo=True,
            criado_em=_now(),
        )
        self._session.add(modelo)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise EmailDuplicado(f"O e-mail '{email}' já está em uso por outro usuário.") from exc
        return _usuario_para_entidade(modelo)

    async def listar(self, *, page: int, per_page: int) -> tuple[list[Usuario], int]:
        offset, limit = offset_limit(page=page, per_page=per_page)
        total = await self._session.scalar(select(func.count()).select_from(UsuarioModel))
        resultado = await self._session.execute(
            select(UsuarioModel).order_by(UsuarioModel.nome).offset(offset).limit(limit)
        )
        usuarios = [_usuario_para_entidade(m) for m in resultado.scalars().all()]
        return usuarios, int(total or 0)

    async def buscar_por_id(self, usuario_id: UUID) -> Usuario | None:
        modelo = await self._session.get(UsuarioModel, usuario_id)
        return _usuario_para_entidade(modelo) if modelo else None

    async def atualizar(
        self, usuario_id: UUID, *, nome: str, papel: PapelUsuario, ativo: bool
    ) -> Usuario | None:
        modelo = await self._session.get(UsuarioModel, usuario_id)
        if modelo is None:
            return None
        modelo.nome = nome
        modelo.papel = papel.value
        modelo.ativo = ativo
        await self._session.flush()
        return _usuario_para_entidade(modelo)

    async def atualizar_senha(self, usuario_id: UUID, senha_hash: str) -> bool:
        modelo = await self._session.get(UsuarioModel, usuario_id)
        if modelo is None:
            return False
        modelo.senha_hash = senha_hash
        await self._session.flush()
        return True

    async def inativar(self, usuario_id: UUID) -> bool:
        modelo = await self._session.get(UsuarioModel, usuario_id)
        if modelo is None:
            return False
        modelo.ativo = False
        await self._session.flush()
        return True

    async def contar_admins_ativos(self) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(UsuarioModel)
            .where(UsuarioModel.papel == PapelUsuario.ADMIN.value, UsuarioModel.ativo.is_(True))
        )
        return int(total or 0)


def _usuario_para_entidade(modelo: UsuarioModel) -> Usuario:
    return Usuario(
        id=modelo.id,
        nome=modelo.nome,
        email=modelo.email,
        senha_hash=modelo.senha_hash,
        papel=PapelUsuario(modelo.papel),
        ativo=modelo.ativo,
        criado_em=modelo.criado_em,
    )
