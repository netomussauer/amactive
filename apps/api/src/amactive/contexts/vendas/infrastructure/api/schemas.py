"""Schemas HTTP (Pydantic) — espelham docs/openapi.yaml (Pedidos)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from amactive.contexts.vendas.domain.entities import FormaPagamento
from amactive.shared_kernel.schemas import Pagination


class ItemPedidoRequest(BaseModel):
    variante_id: UUID
    quantidade: int = Field(ge=1)
    desconto_item: str = Field(default="0.00", pattern=r"^\d+\.\d{2}$")


class PagamentoRequest(BaseModel):
    forma_pagamento: FormaPagamento
    valor: str = Field(pattern=r"^\d+\.\d{2}$")


class CriarPedidoRequest(BaseModel):
    cliente_id: UUID | None = None
    desconto: str = Field(default="0.00", pattern=r"^\d+\.\d{2}$")
    observacao: str | None = None
    itens: list[ItemPedidoRequest] = Field(min_length=1)
    pagamentos: list[PagamentoRequest] = Field(min_length=1)


class ItemPedidoResponse(BaseModel):
    id: UUID
    variante_id: UUID
    sku: str
    quantidade: int
    preco_unitario: str
    desconto_item: str
    subtotal: str


class PagamentoResponse(BaseModel):
    id: UUID
    forma_pagamento: str
    valor: str


class PedidoResponse(BaseModel):
    id: UUID
    numero: str
    cliente_id: UUID | None
    usuario_id: UUID
    status: str
    subtotal: str
    desconto: str
    valor_total: str
    criado_em: datetime
    confirmado_em: datetime | None


class PedidoDetalheResponse(PedidoResponse):
    itens: list[ItemPedidoResponse]
    pagamentos: list[PagamentoResponse]


class PedidoListResponse(BaseModel):
    data: list[PedidoResponse]
    pagination: Pagination
