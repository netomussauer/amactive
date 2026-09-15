"""Implementações concretas de `ClienteRepository`/`FornecedorRepository`."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.cadastros.domain.entities import Cliente, Fornecedor, OrigemCadastroCliente
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

    async def upsert_por_email(
        self,
        *,
        email: str,
        nome: str,
        cpf_cnpj: str | None,
        telefone: str | None,
        endereco_logradouro: str | None,
        endereco_cidade: str | None,
        endereco_uf: str | None,
        endereco_cep: str | None,
        cliente_externo_id: str,
        origem_cadastro: OrigemCadastroCliente,
    ) -> Cliente:
        """`INSERT ... ON CONFLICT (email) DO UPDATE` sobre o índice único
        parcial `uq_cliente_email_nao_nulo` — ver docs/design-integracao-
        nuvemshop.md §3.3. Atômico por construção (evita a condição de
        corrida de um "buscar depois criar/atualizar" em duas etapas sob
        múltiplas réplicas do worker).

        `origem_cadastro` nunca é sobrescrito num conflito (reflete como o
        registro nasceu, não o último canal que o tocou).
        `cliente_externo_id` só é gravado via `COALESCE` se o cliente
        existente ainda não tiver um (nunca substitui um valor já gravado).
        Os demais campos (nome/cpf_cnpj/telefone/endereço) são sempre
        atualizados — dados mais recentes vindos do pedido.
        """
        insert_stmt = pg_insert(ClienteModel).values(
            id=uuid.uuid4(),
            nome=nome,
            cpf_cnpj=cpf_cnpj,
            email=email,
            telefone=telefone,
            endereco_logradouro=endereco_logradouro,
            endereco_cidade=endereco_cidade,
            endereco_uf=endereco_uf,
            endereco_cep=endereco_cep,
            ativo=True,
            criado_em=_now(),
            cliente_externo_id=cliente_externo_id,
            origem_cadastro=origem_cadastro.value,
        )
        stmt = (
            insert_stmt.on_conflict_do_update(
                index_elements=[ClienteModel.email],
                index_where=ClienteModel.email.isnot(None),
                set_={
                    "nome": insert_stmt.excluded.nome,
                    "cpf_cnpj": insert_stmt.excluded.cpf_cnpj,
                    "telefone": insert_stmt.excluded.telefone,
                    "endereco_logradouro": insert_stmt.excluded.endereco_logradouro,
                    "endereco_cidade": insert_stmt.excluded.endereco_cidade,
                    "endereco_uf": insert_stmt.excluded.endereco_uf,
                    "endereco_cep": insert_stmt.excluded.endereco_cep,
                    "cliente_externo_id": func.coalesce(
                        ClienteModel.cliente_externo_id, insert_stmt.excluded.cliente_externo_id
                    ),
                    # origem_cadastro deliberadamente ausente do SET — nunca
                    # sobrescrito num conflito.
                },
            )
            # Colunas explícitas (não o `ClienteModel` inteiro) — evita
            # depender do suporte a ORM-enabled INSERT...RETURNING para um
            # statement dialect-specific (`ON CONFLICT`), mantendo o mesmo
            # estilo de mapeamento manual já usado no resto deste módulo.
            .returning(
                ClienteModel.id,
                ClienteModel.nome,
                ClienteModel.cpf_cnpj,
                ClienteModel.email,
                ClienteModel.telefone,
                ClienteModel.endereco_logradouro,
                ClienteModel.endereco_cidade,
                ClienteModel.endereco_uf,
                ClienteModel.endereco_cep,
                ClienteModel.ativo,
                ClienteModel.criado_em,
                ClienteModel.cliente_externo_id,
                ClienteModel.origem_cadastro,
            )
        )
        try:
            resultado = await self._session.execute(stmt)
        except IntegrityError as exc:
            await self._session.rollback()
            raise DocumentoDuplicado("CPF/CNPJ já cadastrado para outro cliente.") from exc
        linha = resultado.mappings().one()
        await self._session.flush()
        return Cliente(
            id=linha["id"],
            nome=linha["nome"],
            cpf_cnpj=linha["cpf_cnpj"],
            email=linha["email"],
            telefone=linha["telefone"],
            endereco_logradouro=linha["endereco_logradouro"],
            endereco_cidade=linha["endereco_cidade"],
            endereco_uf=linha["endereco_uf"],
            endereco_cep=linha["endereco_cep"],
            ativo=linha["ativo"],
            criado_em=linha["criado_em"],
            cliente_externo_id=linha["cliente_externo_id"],
            origem_cadastro=OrigemCadastroCliente(linha["origem_cadastro"]),
        )


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
        cliente_externo_id=modelo.cliente_externo_id,
        origem_cadastro=OrigemCadastroCliente(modelo.origem_cadastro),
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
