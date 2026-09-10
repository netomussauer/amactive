"""Schemas HTTP (Pydantic) — espelham docs/openapi.yaml (Clientes, Fornecedores)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from amactive.shared_kernel.schemas import Pagination


class CriarClienteRequest(BaseModel):
    nome: str = Field(max_length=150)
    cpf_cnpj: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    endereco_logradouro: str | None = None
    endereco_cidade: str | None = None
    endereco_uf: str | None = Field(default=None, min_length=2, max_length=2)
    endereco_cep: str | None = None


class ClienteResponse(CriarClienteRequest):
    id: UUID
    ativo: bool
    criado_em: datetime


class ClienteListResponse(BaseModel):
    data: list[ClienteResponse]
    pagination: Pagination


class CriarFornecedorRequest(BaseModel):
    razao_social: str = Field(max_length=150)
    nome_fantasia: str | None = None
    cnpj: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    endereco_logradouro: str | None = None
    endereco_cidade: str | None = None
    endereco_uf: str | None = Field(default=None, min_length=2, max_length=2)
    endereco_cep: str | None = None


class FornecedorResponse(CriarFornecedorRequest):
    id: UUID
    ativo: bool
    criado_em: datetime


class FornecedorListResponse(BaseModel):
    data: list[FornecedorResponse]
    pagination: Pagination
