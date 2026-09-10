"""DTOs de entrada dos casos de uso de Vendas (desacoplados dos schemas HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from amactive.contexts.vendas.domain.entities import FormaPagamento


@dataclass(frozen=True)
class ItemPedidoInput:
    variante_id: UUID
    quantidade: int
    desconto_item: Decimal


@dataclass(frozen=True)
class PagamentoInput:
    forma_pagamento: FormaPagamento
    valor: Decimal
