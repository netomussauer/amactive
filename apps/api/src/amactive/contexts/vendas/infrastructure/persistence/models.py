"""Modelos SQLAlchemy do contexto Vendas — mapeiam
migrations/000001_initial_schema.up.sql."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from amactive.shared_kernel.database import Base
from amactive.shared_kernel.pg_enums import forma_pagamento_enum, status_pedido_enum


class PedidoModel(Base):
    __tablename__ = "pedido"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    numero: Mapped[str] = mapped_column(String(20), unique=True)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("cliente.id", ondelete="SET NULL")
    )
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuario.id", ondelete="RESTRICT"))
    status: Mapped[str] = mapped_column(status_pedido_enum)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    desconto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    confirmado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ItemPedidoModel(Base):
    __tablename__ = "item_pedido"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pedido.id", ondelete="CASCADE"))
    variante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produto_variante.id", ondelete="RESTRICT")
    )
    quantidade: Mapped[int] = mapped_column(Integer)
    preco_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    desconto_item: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2))


class PagamentoPedidoModel(Base):
    __tablename__ = "pagamento_pedido"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    pedido_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pedido.id", ondelete="CASCADE"))
    forma_pagamento: Mapped[str] = mapped_column(forma_pagamento_enum)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
