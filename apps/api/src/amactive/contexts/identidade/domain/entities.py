"""Entidades do contexto Identidade & Acesso — ver docs/SDD.md ADR-007."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class PapelUsuario(str, Enum):
    ADMIN = "ADMIN"
    VENDEDOR = "VENDEDOR"
    ESTOQUISTA = "ESTOQUISTA"


@dataclass(frozen=True)
class Usuario:
    id: UUID
    nome: str
    email: str
    senha_hash: str
    papel: PapelUsuario
    ativo: bool
