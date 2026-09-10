"""Schemas HTTP (Pydantic) do contexto Identidade — espelham docs/openapi.yaml."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


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
