"""Controller (FastAPI APIRouter) do contexto Identidade & Acesso."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.identidade.application.use_cases.autenticar_usuario import (
    AutenticarUsuarioUseCase,
)
from amactive.contexts.identidade.infrastructure.api.schemas import (
    LoginRequest,
    LoginResponse,
    UsuarioResponse,
)
from amactive.contexts.identidade.infrastructure.persistence.repositories import (
    SqlAlchemyUsuarioRepository,
)
from amactive.shared_kernel.database import get_db_session

router = APIRouter(prefix="/auth", tags=["Auth"])


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
