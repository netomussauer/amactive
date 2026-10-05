"""Filtros e ordenação da vitrine contra o Postgres real: faixa de preço usa o
preço EFETIVO (com desconto promocional), ordenação por preço nos dois sentidos,
filtro por cor e as opções exibidas no filtro."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import (
    ProdutoModel,
    ProdutoVarianteModel,
)
from amactive.contexts.vitrine.infrastructure.persistence import consultas
from amactive.shared_kernel.exceptions import ErroDeValidacao

pytestmark = pytest.mark.integration

# Nome fixo usado pela fixture criar_variante_com_estoque (tests/integration/conftest.py).
NOME = "Legging Fitness Teste"


async def _listar(session: AsyncSession, **filtros) -> tuple[list[UUID], int]:
    produtos, total = await consultas.listar_produtos(
        session,
        agora=datetime.now(UTC),
        page=1,
        per_page=60,
        categoria_id=None,
        busca=NOME,
        **filtros,
    )
    return [p.id for p in produtos], total


async def _produto_da_variante(session: AsyncSession, variante_id: UUID) -> UUID:
    return await session.scalar(
        select(ProdutoVarianteModel.produto_id).where(ProdutoVarianteModel.id == variante_id)
    )


async def _definir_desconto(session: AsyncSession, variante_id: UUID, percentual: int) -> None:
    produto_id = await _produto_da_variante(session, variante_id)
    await session.execute(
        update(ProdutoModel)
        .where(ProdutoModel.id == produto_id)
        .values(desconto_percentual=Decimal(percentual))
    )


async def test_faixa_de_preco_usa_o_preco_efetivo(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    # A: 100,00 sem desconto (efetivo 100). B: 50,00 com 20% de desconto (efetivo 40).
    await criar_variante_com_estoque(quantidade_inicial=1, preco_venda="100.00")
    b = await criar_variante_com_estoque(quantidade_inicial=1, preco_venda="50.00")
    await _definir_desconto(db_session, b.id, 20)

    ids, total = await _listar(db_session, preco_max=Decimal(45))

    assert total == 1
    assert ids == [await _produto_da_variante(db_session, b.id)]


async def test_ordenacao_por_preco_nos_dois_sentidos(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    await criar_variante_com_estoque(quantidade_inicial=1, preco_venda="100.00")
    b = await criar_variante_com_estoque(quantidade_inicial=1, preco_venda="50.00")
    await _definir_desconto(db_session, b.id, 20)

    asc, _ = await _listar(db_session, ordem="preco_asc")
    desc, _ = await _listar(db_session, ordem="preco_desc")

    assert len(asc) == 2
    assert asc == list(reversed(desc))
    # Mais barato primeiro no crescente: B (efetivo 40) antes de A (100).
    assert asc[0] == await _produto_da_variante(db_session, b.id)


async def test_filtro_de_cor_e_tamanho(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    # A fixture cria variantes Preto/M.
    await criar_variante_com_estoque(quantidade_inicial=1, preco_venda="80.00")

    com_cor, _ = await _listar(db_session, cor="Preto", tamanho="M")
    sem_cor, total = await _listar(db_session, cor="Vermelho")

    assert len(com_cor) == 1
    assert sem_cor == []
    assert total == 0


async def test_opcoes_do_filtro_so_trazem_o_que_se_vende(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    await criar_variante_com_estoque(quantidade_inicial=1, preco_venda="80.00")

    opcoes = await consultas.listar_opcoes_filtro(db_session)

    assert "Preto" in opcoes.cores
    assert "M" in opcoes.tamanhos


async def test_ordenacao_invalida_e_recusada(db_session: AsyncSession) -> None:
    with pytest.raises(ErroDeValidacao):
        await consultas.listar_produtos(
            db_session,
            agora=datetime.now(UTC),
            page=1,
            per_page=10,
            categoria_id=None,
            busca=None,
            ordem="aleatoria",
        )
