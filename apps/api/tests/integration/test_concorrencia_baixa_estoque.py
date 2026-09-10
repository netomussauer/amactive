"""Teste de concorrência REAL (múltiplas conexões/transações simultâneas) —
ver docs/data-model.md § Estratégia de Concorrência — Baixa de Estoque.

Diferente dos demais testes de integração deste pacote (que usam a fixture
`db_session`, uma única conexão/transação por teste, revertida no teardown),
este teste precisa de dados REALMENTE committed e de N conexões
independentes disputando a mesma linha de `estoque` ao mesmo tempo — por
isso usa `test_engine` diretamente, com commit explícito no setup e limpeza
manual no `finally`.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from amactive.contexts.catalogo_estoque.domain.entities import MotivoMovimentacao, TipoMovimentacao
from amactive.contexts.catalogo_estoque.domain.exceptions import SaldoDeEstoqueInsuficiente
from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import (
    MovimentacaoEstoqueModel,
    ProdutoModel,
    ProdutoVarianteModel,
)
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyEstoqueRepository,
    SqlAlchemyMovimentacaoRepository,
)
from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel

pytestmark = pytest.mark.integration


async def test_baixa_concorrente_nunca_deixa_estoque_negativo(test_engine: AsyncEngine) -> None:
    """N tentativas concorrentes de baixar 1 unidade cada de um saldo menor
    que N: exatamente `saldo_inicial` devem ter sucesso, o restante deve
    falhar com `SaldoDeEstoqueInsuficiente`, e o saldo final nunca fica
    negativo — garantia do trigger `fn_aplicar_movimentacao_estoque` sob
    READ COMMITTED (o UPDATE atômico elimina a janela clássica de corrida
    de um SELECT seguido de UPDATE)."""
    saldo_inicial = 3
    num_tentativas = 10

    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    usuario = UsuarioModel(
        id=uuid.uuid4(),
        nome="Usuário Concorrência",
        email=f"concorrencia-{uuid.uuid4().hex[:8]}@amactive.dev",
        senha_hash="x",
        papel="VENDEDOR",
        ativo=True,
        criado_em=datetime.now(UTC),
    )
    produto = ProdutoModel(
        id=uuid.uuid4(),
        nome="Produto Concorrência",
        descricao=None,
        categoria_id=None,
        marca="AMACTIVE",
        ativo=True,
        criado_em=datetime.now(UTC),
    )
    variante = ProdutoVarianteModel(
        id=uuid.uuid4(),
        produto_id=produto.id,
        sku=f"SKU-CONC-{uuid.uuid4().hex[:8].upper()}",
        tamanho="M",
        cor="Preto",
        preco_venda=Decimal("50.00"),
        preco_custo=None,
        ativo=True,
        criado_em=datetime.now(UTC),
    )

    async with session_factory() as setup_session:
        setup_session.add_all([usuario, produto])
        await setup_session.flush()
        setup_session.add(variante)
        await setup_session.flush()
        await SqlAlchemyMovimentacaoRepository(setup_session).registrar(
            variante_id=variante.id,
            tipo=TipoMovimentacao.ENTRADA,
            quantidade=saldo_inicial,
            motivo=MotivoMovimentacao.AJUSTE_INVENTARIO,
            usuario_id=usuario.id,
        )
        await setup_session.commit()

    async def _tentar_baixar_uma_unidade() -> bool:
        async with session_factory() as session:
            try:
                await SqlAlchemyMovimentacaoRepository(session).registrar(
                    variante_id=variante.id,
                    tipo=TipoMovimentacao.SAIDA,
                    quantidade=1,
                    motivo=MotivoMovimentacao.PERDA,
                    usuario_id=usuario.id,
                )
                await session.commit()
                return True
            except SaldoDeEstoqueInsuficiente:
                return False

    try:
        resultados = await asyncio.gather(
            *[_tentar_baixar_uma_unidade() for _ in range(num_tentativas)]
        )
        sucessos = sum(1 for r in resultados if r)
        falhas = sum(1 for r in resultados if not r)

        assert sucessos == saldo_inicial
        assert falhas == num_tentativas - saldo_inicial

        async with session_factory() as verify_session:
            estoque = await SqlAlchemyEstoqueRepository(verify_session).buscar_por_variante(
                variante.id
            )
            assert estoque is not None
            assert estoque.quantidade == 0  # exatamente esgotado, nunca negativo
    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(
                delete(MovimentacaoEstoqueModel).where(
                    MovimentacaoEstoqueModel.variante_id == variante.id
                )
            )
            await cleanup_session.execute(
                delete(ProdutoVarianteModel).where(ProdutoVarianteModel.id == variante.id)
            )
            await cleanup_session.execute(delete(ProdutoModel).where(ProdutoModel.id == produto.id))
            await cleanup_session.execute(delete(UsuarioModel).where(UsuarioModel.id == usuario.id))
            await cleanup_session.commit()
