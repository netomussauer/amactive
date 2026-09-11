from __future__ import annotations

from decimal import Decimal

import pytest

from amactive.shared_kernel.money import aplicar_desconto_percentual, parse_money, to_money_str

pytestmark = pytest.mark.unit


def test_to_money_str_formata_duas_casas() -> None:
    assert to_money_str(Decimal(10)) == "10.00"
    assert to_money_str(Decimal("10.5")) == "10.50"
    assert to_money_str(Decimal("10.005")) == "10.01"  # ROUND_HALF_UP


def test_parse_money_roundtrip() -> None:
    assert parse_money("129.90") == Decimal("129.90")
    assert to_money_str(parse_money("129.90")) == "129.90"


def test_aplicar_desconto_percentual_arredonda_meio_para_cima() -> None:
    # 99.90 * 0.85 = 84.915 -> ROUND_HALF_UP -> 84.92 (não pode divergir por
    # erro de ponto flutuante: 99.90 * 0.85 em float dá 84.91499999999999...).
    resultado = aplicar_desconto_percentual(Decimal("99.90"), Decimal(15))
    assert resultado == Decimal("84.92")


def test_aplicar_desconto_percentual_sem_desconto_preserva_preco() -> None:
    # Não é um caminho de negócio válido (desconto_percentual=0 é rejeitado
    # na camada de validação — ver 0% == "sem promoção" == NULL), mas o
    # helper em si deve ser matematicamente correto em qualquer fronteira.
    assert aplicar_desconto_percentual(Decimal("50.00"), Decimal(0)) == Decimal("50.00")


def test_aplicar_desconto_percentual_100_por_cento_zera_preco() -> None:
    assert aplicar_desconto_percentual(Decimal("199.90"), Decimal(100)) == Decimal("0.00")


def test_aplicar_desconto_percentual_com_preco_custo_quebrado() -> None:
    # 129.90 * 0.90 = 116.91 exato — cobre o caso "redondo" sem dependência
    # de arredondamento, garantindo que o caminho feliz também bate com uma
    # calculadora comum.
    resultado = aplicar_desconto_percentual(Decimal("129.90"), Decimal(10))
    assert resultado == Decimal("116.91")
