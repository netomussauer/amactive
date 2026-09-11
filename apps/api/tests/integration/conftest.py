"""Fixtures de integração — exigem um Postgres real acessível (ver
apps/api/README.md § Testes). Usa o padrão oficial do SQLAlchemy 2.x para
isolamento de testes: uma transação externa por teste, com a Session ligada
a ela via `join_transaction_mode="create_savepoint"` — qualquer
commit/rollback feito pelo código de aplicação vira um SAVEPOINT, e a
transação externa é sempre revertida no teardown (nenhum teste suja o
próximo, sem precisar de TRUNCATE manual).
"""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import asyncpg
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Importa o app inteiro (não só os módulos usados por cada arquivo de teste)
# para garantir que os modelos ORM de TODOS os contextos sejam registrados em
# `Base.metadata` antes de qualquer flush. Sem isso, o topological sort de
# tabelas do SQLAlchemy (usado para ordenar INSERTs entre tabelas com FK)
# falha ao resolver colunas como `movimentacao_estoque.fornecedor_id` quando
# um arquivo de teste isolado nunca importa `FornecedorModel` — algo que não
# acontece na aplicação real porque `main.py` importa todos os routers (e,
# transitivamente, todos os modelos) na inicialização.
import amactive.main  # noqa: F401
from amactive.contexts.catalogo_estoque.domain.entities import (
    MotivoMovimentacao,
    ProdutoVariante,
    TipoMovimentacao,
)
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyMovimentacaoRepository,
    SqlAlchemyProdutoRepository,
    SqlAlchemyVarianteRepository,
)
from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://amactive:amactive@localhost:5432/amactive_test"
)
_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "migrations"


def _asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _garantir_banco_de_teste() -> None:
    dsn = _asyncpg_dsn(TEST_DATABASE_URL)
    base_dsn, _, dbname = dsn.rpartition("/")
    conn = await asyncpg.connect(dsn=f"{base_dsn}/postgres")
    try:
        existe = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname)
        if not existe:
            await conn.execute(f'CREATE DATABASE "{dbname}"')
    finally:
        await conn.close()


async def _aplicar_migrations() -> None:
    """Aplica migrations pendentes, rastreando por arquivo (mesmo padrão de
    `scripts/apply_migrations.py`) em vez de checar só se uma tabela
    conhecida existe — a checagem antiga parava de aplicar qualquer coisa
    assim que a primeira migration já tivesse rodado, então uma migration
    nova (ex.: 000003+) nunca seria pega num banco de teste que persiste
    entre execuções."""
    conn = await asyncpg.connect(dsn=_asyncpg_dsn(TEST_DATABASE_URL))
    try:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                versao text PRIMARY KEY,
                aplicada_em timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        aplicadas = {
            row["versao"] for row in await conn.fetch("SELECT versao FROM schema_migrations")
        }
        for arquivo in sorted(_MIGRATIONS_DIR.glob("*.up.sql")):
            if arquivo.name in aplicadas:
                continue
            await conn.execute(arquivo.read_text(encoding="utf-8"))
            await conn.execute("INSERT INTO schema_migrations (versao) VALUES ($1)", arquivo.name)
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    await _garantir_banco_de_teste()
    await _aplicar_migrations()
    engine = create_async_engine(TEST_DATABASE_URL)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async with test_engine.connect() as conn:
        outer_tx = await conn.begin()
        session_factory = async_sessionmaker(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        async with session_factory() as session:
            yield session
        await outer_tx.rollback()


@pytest_asyncio.fixture
async def usuario_teste(db_session: AsyncSession) -> UsuarioModel:
    usuario = UsuarioModel(
        id=uuid.uuid4(),
        nome="Usuário de Teste",
        email=f"teste-{uuid.uuid4().hex[:8]}@amactive.dev",
        senha_hash="hash-nao-usado-neste-teste",
        papel="VENDEDOR",
        ativo=True,
        criado_em=datetime.now(UTC),
    )
    db_session.add(usuario)
    # `commit()` aqui apenas libera o SAVEPOINT atual (join_transaction_mode
    # ="create_savepoint" — ver docstring do módulo), protegendo este dado de
    # setup de um `rollback()` que o próprio código de produção dispare mais
    # tarde no teste (ex.: ao testar o caminho de erro de saldo insuficiente,
    # que faz um ROLLBACK TO SAVEPOINT interno). A limpeza real acontece de
    # qualquer forma no teardown, via `outer_tx.rollback()`.
    await db_session.commit()
    return usuario


@pytest_asyncio.fixture
async def criar_variante_com_estoque(
    db_session: AsyncSession, usuario_teste: UsuarioModel
) -> Callable[..., Awaitable[ProdutoVariante]]:
    """Factory fixture: cria produto + variante + saldo inicial (via
    movimentação ENTRADA, nunca UPDATE direto — mesma regra da aplicação)."""

    async def _factory(
        *, quantidade_inicial: int = 10, preco_venda: str = "99.90"
    ) -> ProdutoVariante:
        produto_repo = SqlAlchemyProdutoRepository(db_session)
        produto = await produto_repo.criar(
            nome="Legging Fitness Teste", descricao=None, categoria_id=None, marca="AMACTIVE"
        )
        variante_repo = SqlAlchemyVarianteRepository(db_session)
        variante = await variante_repo.criar(
            produto_id=produto.id,
            sku=f"SKU-TESTE-{uuid.uuid4().hex[:8].upper()}",
            tamanho="M",
            cor="Preto",
            preco_venda=Decimal(preco_venda),
            preco_custo=None,
        )
        if quantidade_inicial > 0:
            mov_repo = SqlAlchemyMovimentacaoRepository(db_session)
            await mov_repo.registrar(
                variante_id=variante.id,
                tipo=TipoMovimentacao.ENTRADA,
                quantidade=quantidade_inicial,
                motivo=MotivoMovimentacao.AJUSTE_INVENTARIO,
                usuario_id=usuario_teste.id,
            )
        # Ver comentário em `usuario_teste` — protege este fixture de setup
        # de um rollback interno disparado por um teste de caminho de erro.
        await db_session.commit()
        return variante

    return _factory
