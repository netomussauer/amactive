"""Controllers (FastAPI APIRouter) do contexto Cadastros."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.cadastros.application.use_cases.cliente_use_cases import (
    AtualizarClienteCommand,
    CriarClienteCommand,
    InativarClienteCommand,
    ListarClientesQuery,
    ObterClienteQuery,
)
from amactive.contexts.cadastros.application.use_cases.fornecedor_use_cases import (
    AtualizarFornecedorCommand,
    CriarFornecedorCommand,
    InativarFornecedorCommand,
    ListarFornecedoresQuery,
    ObterFornecedorQuery,
)
from amactive.contexts.cadastros.domain.entities import Cliente, Fornecedor
from amactive.contexts.cadastros.infrastructure.api.schemas import (
    ClienteListResponse,
    ClienteResponse,
    CriarClienteRequest,
    CriarFornecedorRequest,
    FornecedorListResponse,
    FornecedorResponse,
)
from amactive.contexts.cadastros.infrastructure.persistence.repositories import (
    SqlAlchemyClienteRepository,
    SqlAlchemyFornecedorRepository,
)
from amactive.core.security import requer_papel
from amactive.shared_kernel.database import get_db_session
from amactive.shared_kernel.schemas import Pagination

router = APIRouter()

# Clientes: leitura e escrita restritas a ADMIN/VENDEDOR (ESTOQUISTA não
# acessa este recurso — ver matriz de permissões em docs/openapi.yaml).
_requer_acesso_clientes = requer_papel("ADMIN", "VENDEDOR")
# Fornecedores: leitura e escrita restritas a ADMIN/ESTOQUISTA (VENDEDOR não
# acessa este recurso).
_requer_acesso_fornecedores = requer_papel("ADMIN", "ESTOQUISTA")


# ── Clientes ──
@router.get(
    "/clientes",
    tags=["Clientes"],
    response_model=ClienteListResponse,
    dependencies=[Depends(_requer_acesso_clientes)],
)
async def listar_clientes(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    busca: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> ClienteListResponse:
    clientes, total = await ListarClientesQuery(SqlAlchemyClienteRepository(session)).executar(
        page=page, per_page=per_page, busca=busca
    )
    return ClienteListResponse(
        data=[_cliente_response(c) for c in clientes],
        pagination=Pagination(total=total, page=page, per_page=per_page),
    )


@router.post(
    "/clientes",
    tags=["Clientes"],
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_requer_acesso_clientes)],
)
async def criar_cliente(
    payload: CriarClienteRequest, session: AsyncSession = Depends(get_db_session)
) -> ClienteResponse:
    cliente = await CriarClienteCommand(SqlAlchemyClienteRepository(session)).executar(
        **payload.model_dump()
    )
    await session.commit()
    return _cliente_response(cliente)


@router.get(
    "/clientes/{cliente_id}",
    tags=["Clientes"],
    response_model=ClienteResponse,
    dependencies=[Depends(_requer_acesso_clientes)],
)
async def obter_cliente(
    cliente_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> ClienteResponse:
    cliente = await ObterClienteQuery(SqlAlchemyClienteRepository(session)).executar(cliente_id)
    return _cliente_response(cliente)


@router.put(
    "/clientes/{cliente_id}",
    tags=["Clientes"],
    response_model=ClienteResponse,
    dependencies=[Depends(_requer_acesso_clientes)],
)
async def atualizar_cliente(
    cliente_id: UUID,
    payload: CriarClienteRequest,
    session: AsyncSession = Depends(get_db_session),
) -> ClienteResponse:
    cliente = await AtualizarClienteCommand(SqlAlchemyClienteRepository(session)).executar(
        cliente_id, **payload.model_dump()
    )
    await session.commit()
    return _cliente_response(cliente)


@router.delete(
    "/clientes/{cliente_id}",
    tags=["Clientes"],
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_requer_acesso_clientes)],
)
async def inativar_cliente(
    cliente_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> None:
    await InativarClienteCommand(SqlAlchemyClienteRepository(session)).executar(cliente_id)
    await session.commit()


# ── Fornecedores ──
@router.get(
    "/fornecedores",
    tags=["Fornecedores"],
    response_model=FornecedorListResponse,
    dependencies=[Depends(_requer_acesso_fornecedores)],
)
async def listar_fornecedores(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    busca: str | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> FornecedorListResponse:
    fornecedores, total = await ListarFornecedoresQuery(
        SqlAlchemyFornecedorRepository(session)
    ).executar(page=page, per_page=per_page, busca=busca)
    return FornecedorListResponse(
        data=[_fornecedor_response(f) for f in fornecedores],
        pagination=Pagination(total=total, page=page, per_page=per_page),
    )


@router.post(
    "/fornecedores",
    tags=["Fornecedores"],
    response_model=FornecedorResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_requer_acesso_fornecedores)],
)
async def criar_fornecedor(
    payload: CriarFornecedorRequest, session: AsyncSession = Depends(get_db_session)
) -> FornecedorResponse:
    fornecedor = await CriarFornecedorCommand(SqlAlchemyFornecedorRepository(session)).executar(
        **payload.model_dump()
    )
    await session.commit()
    return _fornecedor_response(fornecedor)


@router.get(
    "/fornecedores/{fornecedor_id}",
    tags=["Fornecedores"],
    response_model=FornecedorResponse,
    dependencies=[Depends(_requer_acesso_fornecedores)],
)
async def obter_fornecedor(
    fornecedor_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> FornecedorResponse:
    fornecedor = await ObterFornecedorQuery(SqlAlchemyFornecedorRepository(session)).executar(
        fornecedor_id
    )
    return _fornecedor_response(fornecedor)


@router.put(
    "/fornecedores/{fornecedor_id}",
    tags=["Fornecedores"],
    response_model=FornecedorResponse,
    dependencies=[Depends(_requer_acesso_fornecedores)],
)
async def atualizar_fornecedor(
    fornecedor_id: UUID,
    payload: CriarFornecedorRequest,
    session: AsyncSession = Depends(get_db_session),
) -> FornecedorResponse:
    fornecedor = await AtualizarFornecedorCommand(SqlAlchemyFornecedorRepository(session)).executar(
        fornecedor_id, **payload.model_dump()
    )
    await session.commit()
    return _fornecedor_response(fornecedor)


@router.delete(
    "/fornecedores/{fornecedor_id}",
    tags=["Fornecedores"],
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_requer_acesso_fornecedores)],
)
async def inativar_fornecedor(
    fornecedor_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> None:
    await InativarFornecedorCommand(SqlAlchemyFornecedorRepository(session)).executar(fornecedor_id)
    await session.commit()


def _cliente_response(cliente: Cliente) -> ClienteResponse:
    return ClienteResponse(
        id=cliente.id,
        nome=cliente.nome,
        cpf_cnpj=cliente.cpf_cnpj,
        email=cliente.email,
        telefone=cliente.telefone,
        endereco_logradouro=cliente.endereco_logradouro,
        endereco_cidade=cliente.endereco_cidade,
        endereco_uf=cliente.endereco_uf,
        endereco_cep=cliente.endereco_cep,
        ativo=cliente.ativo,
        criado_em=cliente.criado_em,
    )


def _fornecedor_response(fornecedor: Fornecedor) -> FornecedorResponse:
    return FornecedorResponse(
        id=fornecedor.id,
        razao_social=fornecedor.razao_social,
        nome_fantasia=fornecedor.nome_fantasia,
        cnpj=fornecedor.cnpj,
        email=fornecedor.email,
        telefone=fornecedor.telefone,
        endereco_logradouro=fornecedor.endereco_logradouro,
        endereco_cidade=fornecedor.endereco_cidade,
        endereco_uf=fornecedor.endereco_uf,
        endereco_cep=fornecedor.endereco_cep,
        ativo=fornecedor.ativo,
        criado_em=fornecedor.criado_em,
    )
