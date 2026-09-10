"""Entidades do contexto Vendas — ver docs/data-model.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


class StatusPedido(str, Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    CANCELADO = "CANCELADO"


class FormaPagamento(str, Enum):
    DINHEIRO = "DINHEIRO"
    PIX = "PIX"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    CARTAO_CREDITO = "CARTAO_CREDITO"


@dataclass(frozen=True)
class ItemPedido:
    id: UUID
    variante_id: UUID
    sku: str
    quantidade: int
    preco_unitario: Decimal
    desconto_item: Decimal
    subtotal: Decimal


@dataclass(frozen=True)
class PagamentoPedido:
    id: UUID
    forma_pagamento: FormaPagamento
    valor: Decimal


@dataclass(frozen=True)
class Pedido:
    id: UUID
    numero: str
    cliente_id: UUID | None
    usuario_id: UUID
    status: StatusPedido
    subtotal: Decimal
    desconto: Decimal
    valor_total: Decimal
    observacao: str | None
    criado_em: datetime
    confirmado_em: datetime | None
    cancelado_em: datetime | None
    itens: list[ItemPedido] = field(default_factory=list)
    pagamentos: list[PagamentoPedido] = field(default_factory=list)
