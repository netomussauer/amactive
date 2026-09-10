"""Conversão entre `Decimal` (domínio/banco) e strings monetárias `"123.45"`
(contrato HTTP — ver docs/openapi.yaml, padrão `pattern: '^\\d+\\.\\d{2}$'`)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def to_money_str(valor: Decimal) -> str:
    return str(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_money(valor: str) -> Decimal:
    return Decimal(valor)
