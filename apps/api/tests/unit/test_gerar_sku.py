"""SKU gerado a partir de tamanho e cor, inclusive com acentos."""

from __future__ import annotations

import pytest

from amactive.contexts.catalogo_estoque.application.use_cases.variante_use_cases import gerar_sku

pytestmark = pytest.mark.unit


def test_tamanho_unico_vira_unic_sem_perder_letras() -> None:
    # 'Único' sem acento = 'UNICO'; o SKU usa os 4 primeiros caracteres.
    sku = gerar_sku(tamanho="Único", cor="Preto")

    assert sku.startswith("SKU-UNIC-PRETO-")


def test_cor_com_acento_mantem_as_letras() -> None:
    sku = gerar_sku(tamanho="M", cor="Ônix")

    assert sku.startswith("SKU-M-ONIX-")
