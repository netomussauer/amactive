"""Schemas HTTP (Pydantic) do contexto Identidade — espelham docs/openapi.yaml."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from amactive.contexts.identidade.domain.entities import PapelUsuario
from amactive.shared_kernel.schemas import Pagination


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=8)


class UsuarioResponse(BaseModel):
    id: str
    nome: str
    email: str
    papel: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    usuario: UsuarioResponse


# ── Gestão de usuários (CRUD, ADMIN apenas) ──
class CriarUsuarioRequest(BaseModel):
    nome: str = Field(max_length=150)
    email: EmailStr
    senha: str = Field(min_length=8)
    papel: PapelUsuario


class AtualizarUsuarioRequest(BaseModel):
    """NÃO inclui senha — ver `AtualizarSenhaRequest` (`PATCH /usuarios/{id}/senha`)."""

    nome: str = Field(max_length=150)
    papel: PapelUsuario
    ativo: bool


class AtualizarSenhaRequest(BaseModel):
    senha: str = Field(min_length=8)


class UsuarioDetalheResponse(BaseModel):
    """Nunca inclui `senha_hash` — usada em POST/GET/PUT de `/usuarios`
    (distinta de `UsuarioResponse`, embutida em `LoginResponse`)."""

    id: UUID
    nome: str
    email: str
    papel: str
    ativo: bool
    criado_em: datetime


class UsuarioListResponse(BaseModel):
    data: list[UsuarioDetalheResponse]
    pagination: Pagination
