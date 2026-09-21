"""Schemas HTTP (Pydantic) — espelham docs/openapi.yaml (Pedidos)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from amactive.contexts.vendas.domain.entities import FormaPagamento, OrigemCanalPedido
from amactive.shared_kernel.schemas import Pagination

# Número do pedido no canal de origem (ex.: "#1234" da Nuvemshop). Espaços nas
# pontas são removidos ANTES de validar o tamanho (1..100) — assim " 1234 " e
# "1234" são o mesmo pedido para efeito de duplicidade, e "   " é rejeitado.
PedidoExternoId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


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
    # Registro manual por canal. A coerência entre os dois campos (NUVEMSHOP
    # exige número; PDV e WHATSAPP rejeitam) é regra de domínio,
    # validada em `RegistrarPedidoManualUseCase`.
    origem_canal: OrigemCanalPedido = OrigemCanalPedido.PDV
    pedido_externo_id: PedidoExternoId | None = None


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
    origem_canal: str
    pedido_externo_id: str | None


class PedidoDetalheResponse(PedidoResponse):
    itens: list[ItemPedidoResponse]
    pagamentos: list[PagamentoResponse]


class PedidoListResponse(BaseModel):
    data: list[PedidoResponse]
    pagination: Pagination
