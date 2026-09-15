"""Entidades do contexto Cadastros (Master Data) — Cliente e Fornecedor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class OrigemCadastroCliente(str, Enum):
    """Como o cadastro do cliente nasceu — ver docs/design-integracao-
    nuvemshop.md §2.3/§3.3 (nota de Ubiquitous Language: vocabulário de
    `cadastros`, distinto de `CanalIntegracao` de `integracao_canais`).
    Nunca é sobrescrito por um upsert posterior — reflete a origem, não o
    último canal que tocou o registro."""

    MANUAL = "MANUAL"
    NUVEMSHOP = "NUVEMSHOP"


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
    cliente_externo_id: str | None
    origem_cadastro: OrigemCadastroCliente


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
