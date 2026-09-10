"""Modelos SQLAlchemy do contexto Cadastros — mapeiam
migrations/000001_initial_schema.up.sql."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from amactive.shared_kernel.database import Base


class ClienteModel(Base):
    __tablename__ = "cliente"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(150))
    cpf_cnpj: Mapped[str | None] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    endereco_logradouro: Mapped[str | None] = mapped_column(String(255))
    endereco_cidade: Mapped[str | None] = mapped_column(String(100))
    endereco_uf: Mapped[str | None] = mapped_column(String(2))
    endereco_cep: Mapped[str | None] = mapped_column(String(10))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FornecedorModel(Base):
    __tablename__ = "fornecedor"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    razao_social: Mapped[str] = mapped_column(String(150))
    nome_fantasia: Mapped[str | None] = mapped_column(String(150))
    cnpj: Mapped[str | None] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(255))
    telefone: Mapped[str | None] = mapped_column(String(20))
    endereco_logradouro: Mapped[str | None] = mapped_column(String(255))
    endereco_cidade: Mapped[str | None] = mapped_column(String(100))
    endereco_uf: Mapped[str | None] = mapped_column(String(2))
    endereco_cep: Mapped[str | None] = mapped_column(String(10))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
