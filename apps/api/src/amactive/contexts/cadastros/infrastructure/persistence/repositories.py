"""Implementações concretas de `ClienteRepository`/`FornecedorRepository`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.cadastros.domain.entities import Cliente, Fornecedor
from amactive.contexts.cadastros.domain.exceptions import DocumentoDuplicado
from amactive.contexts.cadastros.infrastructure.persistence.models import (
    ClienteModel,
    FornecedorModel,
)
from amactive.shared_kernel.pagination import offset_limit


def _now() -> datetime:
    return datetime.now(UTC)


class SqlAlchemyClienteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(self, **campos: object) -> Cliente:
        modelo = ClienteModel(id=uuid.uuid4(), ativo=True, criado_em=_now(), **campos)
        self._session.add(modelo)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DocumentoDuplicado("CPF/CNPJ já cadastrado para outro cliente.") from exc
        return _cliente_para_entidade(modelo)

    async def listar(
        self, *, page: int, per_page: int, busca: str | None
    ) -> tuple[list[Cliente], int]:
        offset, limit = offset_limit(page=page, per_page=per_page)
        condicoes = []
        if busca:
            padrao = f"%{busca}%"
            condicoes.append(
                or_(
                    ClienteModel.nome.ilike(padrao),
                    ClienteModel.email.ilike(padrao),
                    ClienteModel.cpf_cnpj.ilike(padrao),
                )
            )
        total = await self._session.scalar(
            select(func.count()).select_from(ClienteModel).where(*condicoes)
        )
        resultado = await self._session.execute(
            select(ClienteModel)
            .where(*condicoes)
            .order_by(ClienteModel.nome)
            .offset(offset)
            .limit(limit)
        )
        clientes = [_cliente_para_entidade(m) for m in resultado.scalars().all()]
        return clientes, int(total or 0)

    async def buscar_por_id(self, cliente_id: UUID) -> Cliente | None:
        modelo = await self._session.get(ClienteModel, cliente_id)
        return _cliente_para_entidade(modelo) if modelo else None

    async def atualizar(self, cliente_id: UUID, **campos: object) -> Cliente | None:
        modelo = await self._session.get(ClienteModel, cliente_id)
        if modelo is None:
            return None
        for chave, valor in campos.items():
            setattr(modelo, chave, valor)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DocumentoDuplicado("CPF/CNPJ já cadastrado para outro cliente.") from exc
        return _cliente_para_entidade(modelo)

    async def inativar(self, cliente_id: UUID) -> bool:
        modelo = await self._session.get(ClienteModel, cliente_id)
        if modelo is None:
            return False
        modelo.ativo = False
        await self._session.flush()
        return True


class SqlAlchemyFornecedorRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(self, **campos: object) -> Fornecedor:
        modelo = FornecedorModel(id=uuid.uuid4(), ativo=True, criado_em=_now(), **campos)
        self._session.add(modelo)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DocumentoDuplicado("CNPJ já cadastrado para outro fornecedor.") from exc
        return _fornecedor_para_entidade(modelo)

    async def listar(
        self, *, page: int, per_page: int, busca: str | None
    ) -> tuple[list[Fornecedor], int]:
        offset, limit = offset_limit(page=page, per_page=per_page)
        condicoes = []
        if busca:
            padrao = f"%{busca}%"
            condicoes.append(
                or_(
                    FornecedorModel.razao_social.ilike(padrao),
                    FornecedorModel.nome_fantasia.ilike(padrao),
                    FornecedorModel.cnpj.ilike(padrao),
                )
            )
        total = await self._session.scalar(
            select(func.count()).select_from(FornecedorModel).where(*condicoes)
        )
        resultado = await self._session.execute(
            select(FornecedorModel)
            .where(*condicoes)
            .order_by(FornecedorModel.razao_social)
            .offset(offset)
            .limit(limit)
        )
        fornecedores = [_fornecedor_para_entidade(m) for m in resultado.scalars().all()]
        return fornecedores, int(total or 0)

    async def buscar_por_id(self, fornecedor_id: UUID) -> Fornecedor | None:
        modelo = await self._session.get(FornecedorModel, fornecedor_id)
        return _fornecedor_para_entidade(modelo) if modelo else None

    async def atualizar(self, fornecedor_id: UUID, **campos: object) -> Fornecedor | None:
        modelo = await self._session.get(FornecedorModel, fornecedor_id)
        if modelo is None:
            return None
        for chave, valor in campos.items():
            setattr(modelo, chave, valor)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise DocumentoDuplicado("CNPJ já cadastrado para outro fornecedor.") from exc
        return _fornecedor_para_entidade(modelo)

    async def inativar(self, fornecedor_id: UUID) -> bool:
        modelo = await self._session.get(FornecedorModel, fornecedor_id)
        if modelo is None:
            return False
        modelo.ativo = False
        await self._session.flush()
        return True


def _cliente_para_entidade(modelo: ClienteModel) -> Cliente:
    return Cliente(
        id=modelo.id,
        nome=modelo.nome,
        cpf_cnpj=modelo.cpf_cnpj,
        email=modelo.email,
        telefone=modelo.telefone,
        endereco_logradouro=modelo.endereco_logradouro,
        endereco_cidade=modelo.endereco_cidade,
        endereco_uf=modelo.endereco_uf,
        endereco_cep=modelo.endereco_cep,
        ativo=modelo.ativo,
        criado_em=modelo.criado_em,
    )


def _fornecedor_para_entidade(modelo: FornecedorModel) -> Fornecedor:
    return Fornecedor(
        id=modelo.id,
        razao_social=modelo.razao_social,
        nome_fantasia=modelo.nome_fantasia,
        cnpj=modelo.cnpj,
        email=modelo.email,
        telefone=modelo.telefone,
        endereco_logradouro=modelo.endereco_logradouro,
        endereco_cidade=modelo.endereco_cidade,
        endereco_uf=modelo.endereco_uf,
        endereco_cep=modelo.endereco_cep,
        ativo=modelo.ativo,
        criado_em=modelo.criado_em,
    )
