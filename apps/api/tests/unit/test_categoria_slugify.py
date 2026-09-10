from __future__ import annotations

import pytest

from amactive.contexts.catalogo_estoque.application.use_cases.categoria_use_cases import slugify

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        ("Leggings", "leggings"),
        ("Top & Sutiã", "top-sutia"),
        ("  Moda Fitness  ", "moda-fitness"),
        ("Conjunto Fitness Feminino", "conjunto-fitness-feminino"),
        ("", "categoria"),
    ],
)
def test_slugify(entrada: str, esperado: str) -> None:
    assert slugify(entrada) == esperado
