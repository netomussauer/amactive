"""Conversão entre `Decimal` (domínio/banco) e strings monetárias `"123.45"`
(contrato HTTP — ver docs/openapi.yaml, padrão `pattern: '^\\d+\\.\\d{2}$'`)."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def to_money_str(valor: Decimal) -> str:
    return str(valor.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def parse_money(valor: str) -> Decimal:
    return Decimal(valor)


def aplicar_desconto_percentual(preco: Decimal, desconto_percentual: Decimal) -> Decimal:
    """Aplica um desconto percentual (ex: `Decimal("15")` = 15%) sobre `preco`,
    retornando o preço já promocional arredondado para 2 casas (ROUND_HALF_UP,
    mesma convenção de `to_money_str`). Sempre em `Decimal` — nunca `float` —
    para não introduzir erro de ponto flutuante no valor cobrado no PDV."""
    fator = Decimal(1) - (desconto_percentual / Decimal(100))
    return (preco * fator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
