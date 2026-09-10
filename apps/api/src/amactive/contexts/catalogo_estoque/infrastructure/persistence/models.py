"""Modelos SQLAlchemy do contexto Catálogo & Estoque — mapeiam
migrations/000001_initial_schema.up.sql. Nunca usados para gerar schema
(sem `Base.metadata.create_all()` — ver docs/SDD.md ADR-003).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from amactive.shared_kernel.database import Base
from amactive.shared_kernel.pg_enums import motivo_movimentacao_enum, tipo_movimentacao_enum


class CategoriaModel(Base):
    __tablename__ = "categoria"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), unique=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProdutoModel(Base):
    __tablename__ = "produto"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    categoria_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("categoria.id", ondelete="SET NULL")
    )
    nome: Mapped[str] = mapped_column(String(200))
    descricao: Mapped[str | None] = mapped_column(Text)
    marca: Mapped[str] = mapped_column(String(100))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProdutoVarianteModel(Base):
    __tablename__ = "produto_variante"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("produto.id", ondelete="RESTRICT"))
    sku: Mapped[str] = mapped_column(String(50), unique=True)
    tamanho: Mapped[str] = mapped_column(String(10))
    cor: Mapped[str] = mapped_column(String(50))
    preco_venda: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    preco_custo: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ativo: Mapped[bool] = mapped_column(Boolean)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EstoqueModel(Base):
    """Somente leitura pela aplicação — o saldo é escrito exclusivamente pelo
    trigger `fn_aplicar_movimentacao_estoque` (ver docs/data-model.md)."""

    __tablename__ = "estoque"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    variante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produto_variante.id", ondelete="CASCADE"), unique=True
    )
    quantidade: Mapped[int] = mapped_column(Integer)
    estoque_minimo: Mapped[int] = mapped_column(Integer)
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MovimentacaoEstoqueModel(Base):
    """Append-only — a aplicação NUNCA faz UPDATE/DELETE nesta tabela, apenas
    INSERT (ver docs/data-model.md decisão #3 e regra crítica de negócio)."""

    __tablename__ = "movimentacao_estoque"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    variante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produto_variante.id", ondelete="RESTRICT")
    )
    tipo: Mapped[str] = mapped_column(tipo_movimentacao_enum)
    quantidade: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str] = mapped_column(motivo_movimentacao_enum)
    pedido_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pedido.id", ondelete="SET NULL")
    )
    fornecedor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fornecedor.id", ondelete="SET NULL")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
