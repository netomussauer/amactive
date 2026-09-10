"""Entidades do contexto Cadastros (Master Data) — Cliente e Fornecedor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class Cliente:
    id: UUID
    nome: str
    cpf_cnpj: str | None
    email: str | None
    telefone: str | None
    endereco_logradouro: str | None
    endereco_cidade: str | None
    endereco_uf: str | None
    endereco_cep: str | None
    ativo: bool
    criado_em: datetime


@dataclass(frozen=True)
class Fornecedor:
    id: UUID
    razao_social: str
    nome_fantasia: str | None
    cnpj: str | None
    email: str | None
    telefone: str | None
    endereco_logradouro: str | None
    endereco_cidade: str | None
    endereco_uf: str | None
    endereco_cep: str | None
    ativo: bool
    criado_em: datetime
