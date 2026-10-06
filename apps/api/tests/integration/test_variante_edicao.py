"""Edição de variante (SKU e tamanho) contra o Postgres real: correção de SKU
funciona, e SKU já usado por outra variante é recusado com erro de negócio
(409), não com erro interno."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.application.use_cases.variante_use_cases import (
    AtualizarVarianteCommand,
)
from amactive.contexts.catalogo_estoque.domain.exceptions import SkuDuplicado
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyVarianteRepository,
)

pytestmark = pytest.mark.integration


async def test_corrige_sku_e_tamanho(db_session: AsyncSession, criar_variante_com_estoque) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=1)

    atualizada = await AtualizarVarianteCommand(SqlAlchemyVarianteRepository(db_session)).executar(
        variante.id, sku="SKU-CORRIGIDO-001", tamanho="Único"
    )

    assert atualizada is not None
    assert atualizada.sku == "SKU-CORRIGIDO-001"
    assert atualizada.tamanho == "Único"


async def test_sku_ja_usado_por_outra_variante_e_recusado(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    primeira = await criar_variante_com_estoque(quantidade_inicial=1)
    segunda = await criar_variante_com_estoque(quantidade_inicial=1)

    with pytest.raises(SkuDuplicado):
        await AtualizarVarianteCommand(SqlAlchemyVarianteRepository(db_session)).executar(
            segunda.id, sku=primeira.sku
        )
