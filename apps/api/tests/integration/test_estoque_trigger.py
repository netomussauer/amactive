"""Testes de integração do trigger `fn_aplicar_movimentacao_estoque`
(ver migrations/000001_initial_schema.up.sql e docs/data-model.md)."""

from __future__ import annotations

import pytest

from amactive.contexts.catalogo_estoque.domain.entities import MotivoMovimentacao, TipoMovimentacao
from amactive.contexts.catalogo_estoque.domain.exceptions import SaldoDeEstoqueInsuficiente
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyEstoqueRepository,
    SqlAlchemyMovimentacaoRepository,
)

pytestmark = pytest.mark.integration


async def test_entrada_incrementa_saldo(db_session, criar_variante_com_estoque) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)

    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)

    assert estoque is not None
    assert estoque.quantidade == 5


async def test_saida_com_saldo_suficiente_decrementa_saldo(
    db_session, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=10)
    mov_repo = SqlAlchemyMovimentacaoRepository(db_session)

    await mov_repo.registrar(
        variante_id=variante.id,
        tipo=TipoMovimentacao.SAIDA,
        quantidade=4,
        motivo=MotivoMovimentacao.PERDA,
        usuario_id=usuario_teste.id,
    )

    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)
    assert estoque.quantidade == 6


async def test_saida_maior_que_saldo_levanta_saldo_insuficiente_com_mensagem_clara(
    db_session, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=2)
    mov_repo = SqlAlchemyMovimentacaoRepository(db_session)

    with pytest.raises(SaldoDeEstoqueInsuficiente) as exc_info:
        await mov_repo.registrar(
            variante_id=variante.id,
            tipo=TipoMovimentacao.SAIDA,
            quantidade=5,
            motivo=MotivoMovimentacao.PERDA,
            usuario_id=usuario_teste.id,
        )

    mensagem = str(exc_info.value)
    assert variante.sku in mensagem
    assert "2" in mensagem
    assert "5" in mensagem


async def test_saida_nunca_deixa_estoque_negativo_mesmo_apos_erro(
    db_session, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=1)
    mov_repo = SqlAlchemyMovimentacaoRepository(db_session)

    with pytest.raises(SaldoDeEstoqueInsuficiente):
        await mov_repo.registrar(
            variante_id=variante.id,
            tipo=TipoMovimentacao.SAIDA,
            quantidade=99,
            motivo=MotivoMovimentacao.PERDA,
            usuario_id=usuario_teste.id,
        )

    # A movimentação recusada não deve ter sido persistida, e o saldo
    # permanece exatamente no valor anterior (nunca negativo).
    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)
    assert estoque is not None
    assert estoque.quantidade == 1
