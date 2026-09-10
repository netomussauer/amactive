from __future__ import annotations

from decimal import Decimal

import pytest

from amactive.shared_kernel.money import parse_money, to_money_str

pytestmark = pytest.mark.unit


def test_to_money_str_formata_duas_casas() -> None:
    assert to_money_str(Decimal(10)) == "10.00"
    assert to_money_str(Decimal("10.5")) == "10.50"
    assert to_money_str(Decimal("10.005")) == "10.01"  # ROUND_HALF_UP


def test_parse_money_roundtrip() -> None:
    assert parse_money("129.90") == Decimal("129.90")
    assert to_money_str(parse_money("129.90")) == "129.90"
