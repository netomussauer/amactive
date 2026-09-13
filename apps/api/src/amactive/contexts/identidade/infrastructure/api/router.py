"""Controllers (FastAPI APIRouter) do contexto Identidade & Acesso.

Dois routers: `router` (`/auth`, login público) e `usuarios_router`
(`/usuarios`, CRUD administrativo — ADMIN apenas, ver
docs/SDD.md ADR-007 / matriz RBAC em docs/openapi.yaml)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.identidade.application.use_cases.autenticar_usuario import (
    AutenticarUsuarioUseCase,
)
from amactive.contexts.identidade.application.use_cases.usuario_use_cases import (
    AtualizarSenhaUsuarioCommand,
    AtualizarUsuarioCommand,
    CriarUsuarioCommand,
    InativarUsuarioCommand,
    ListarUsuariosQuery,
    ObterUsuarioQuery,
)
from amactive.contexts.identidade.domain.entities import Usuario
from amactive.contexts.identidade.infrastructure.api.schemas import (
    AtualizarSenhaRequest,
    AtualizarUsuarioRequest,
    CriarUsuarioRequest,
    LoginRequest,
    LoginResponse,
    UsuarioDetalheResponse,
    UsuarioListResponse,
    UsuarioResponse,
)
from amactive.contexts.identidade.infrastructure.persistence.repositories import (
    SqlAlchemyUsuarioRepository,
)
from amactive.core.security import CurrentUser, requer_papel
from amactive.shared_kernel.database import get_db_session
from amactive.shared_kernel.schemas import Pagination

router = APIRouter(prefix="/auth", tags=["Auth"])
usuarios_router = APIRouter(prefix="/usuarios", tags=["Usuários"])

_requer_admin = requer_papel("ADMIN")


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest, session: AsyncSession = Depends(get_db_session)
) -> LoginResponse:
    use_case = AutenticarUsuarioUseCase(SqlAlchemyUsuarioRepository(session))
    resultado = await use_case.executar(email=payload.email, senha=payload.senha)
    return LoginResponse(
        access_token=resultado.access_token,
        token_type=resultado.token_type,
        usuario=UsuarioResponse(
            id=resultado.usuario_id,
            nome=resultado.nome,
            email=resultado.email,
            papel=resultado.papel,
        ),
    )


# ── Usuários (CRUD administrativo — ADMIN apenas) ──
@usuarios_router.post(
    "",
    response_model=UsuarioDetalheResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_requer_admin)],
)
async def criar_usuario(
    payload: CriarUsuarioRequest, session: AsyncSession = Depends(get_db_session)
) -> UsuarioDetalheResponse:
    usuario = await CriarUsuarioCommand(SqlAlchemyUsuarioRepository(session)).executar(
        nome=payload.nome, email=payload.email, senha=payload.senha, papel=payload.papel
    )
    await session.commit()
    return _usuario_response(usuario)


@usuarios_router.get("", response_model=UsuarioListResponse, dependencies=[Depends(_requer_admin)])
async def listar_usuarios(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> UsuarioListResponse:
    usuarios, total = await ListarUsuariosQuery(SqlAlchemyUsuarioRepository(session)).executar(
        page=page, per_page=per_page
    )
    return UsuarioListResponse(
        data=[_usuario_response(u) for u in usuarios],
        pagination=Pagination(total=total, page=page, per_page=per_page),
    )


@usuarios_router.get(
    "/{usuario_id}", response_model=UsuarioDetalheResponse, dependencies=[Depends(_requer_admin)]
)
async def obter_usuario(
    usuario_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> UsuarioDetalheResponse:
    usuario = await ObterUsuarioQuery(SqlAlchemyUsuarioRepository(session)).executar(usuario_id)
    return _usuario_response(usuario)


@usuarios_router.put("/{usuario_id}", response_model=UsuarioDetalheResponse)
async def atualizar_usuario(
    usuario_id: UUID,
    payload: AtualizarUsuarioRequest,
    admin: CurrentUser = Depends(_requer_admin),
    session: AsyncSession = Depends(get_db_session),
) -> UsuarioDetalheResponse:
    usuario = await AtualizarUsuarioCommand(SqlAlchemyUsuarioRepository(session)).executar(
        usuario_id,
        current_user_id=admin.id,
        nome=payload.nome,
        papel=payload.papel,
        ativo=payload.ativo,
    )
    await session.commit()
    return _usuario_response(usuario)


@usuarios_router.patch(
    "/{usuario_id}/senha",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(_requer_admin)],
)
async def redefinir_senha_usuario(
    usuario_id: UUID,
    payload: AtualizarSenhaRequest,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await AtualizarSenhaUsuarioCommand(SqlAlchemyUsuarioRepository(session)).executar(
        usuario_id, senha=payload.senha
    )
    await session.commit()


@usuarios_router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def inativar_usuario(
    usuario_id: UUID,
    admin: CurrentUser = Depends(_requer_admin),
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await InativarUsuarioCommand(SqlAlchemyUsuarioRepository(session)).executar(
        usuario_id, current_user_id=admin.id
    )
    await session.commit()


def _usuario_response(usuario: Usuario) -> UsuarioDetalheResponse:
    return UsuarioDetalheResponse(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        papel=usuario.papel.value,
        ativo=usuario.ativo,
        criado_em=usuario.criado_em,
    )
