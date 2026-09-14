"""Testes de integração da migration `000004_produto_desconto_promocional`
(ver docs/data-model.md decisão #14) — cobre tanto o schema em si (aplica e
reverte limpo, constraint de range) quanto a exposição via API/PDV do
`preco_promocional` calculado a partir dele.

O teste de aplica/reverte roda `.down.sql` seguido de `.up.sql` diretamente
via `asyncpg` (fora da fixture `db_session`, que usa SAVEPOINT — DDL com
BEGIN/COMMIT próprio não deve ser misturado com aquela transação externa),
sempre restaurando o schema ao estado original em um bloco `finally`, para
não afetar os demais testes da suíte que dependem da coluna existir (ver
`tests/integration/conftest.py::_aplicar_migrations`, que já marca esta
migration como aplicada e nunca a reexecuta)."""

from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

import asyncpg
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration

# Mesma resolução de URL/diretório de `tests/integration/conftest.py` — não
# importada de lá para não acoplar este teste a detalhes internos do
# conftest (símbolos com underscore não são API pública entre módulos).
_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://amactive:amactive@localhost:5432/amactive_test"
)
_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "migrations"


def _asyncpg_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


# Lidos sob demanda (não em import time) pelas mesmas razões de
# `conftest.py::_migrations_dir` — a Task de CI `python-test` copia só
# `apps/api/` para o workspace, sem `migrations/` na raiz do monorepo; ler
# esses arquivos como constante de módulo quebraria a coleta deste arquivo
# de teste mesmo rodando só `pytest -m unit` (que nem seleciona nada daqui).
def _up_sql() -> str:
    return (_MIGRATIONS_DIR / "000004_produto_desconto_promocional.up.sql").read_text(
        encoding="utf-8"
    )


def _down_sql() -> str:
    return (_MIGRATIONS_DIR / "000004_produto_desconto_promocional.down.sql").read_text(
        encoding="utf-8"
    )


_QUERY_COLUNA_EXISTE = """
    SELECT 1 FROM information_schema.columns
     WHERE table_name = 'produto' AND column_name = 'desconto_percentual'
"""


async def test_migration_down_remove_coluna_e_up_recria_com_constraint(test_engine) -> None:
    # `test_engine` não é usado diretamente (este teste fala com o banco via
    # asyncpg cru, não via SQLAlchemy) — é pedido apenas para garantir, via a
    # fixture `session`-scoped, que o banco de teste já existe e todas as
    # migrations (incluindo esta) já foram aplicadas antes deste teste rodar,
    # independentemente da ordem de coleta dos arquivos de teste.
    conn = await asyncpg.connect(dsn=_asyncpg_dsn(_TEST_DATABASE_URL))
    try:
        assert await conn.fetchval(_QUERY_COLUNA_EXISTE) == 1

        await conn.execute(_down_sql())
        assert await conn.fetchval(_QUERY_COLUNA_EXISTE) is None

        await conn.execute(_up_sql())
        assert await conn.fetchval(_QUERY_COLUNA_EXISTE) == 1

        # A constraint de range volta a valer após o up.sql reaplicado.
        produto_id = await conn.fetchval(
            "INSERT INTO produto (nome) VALUES ('Produto Teste Migration') RETURNING id"
        )
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                "UPDATE produto SET desconto_percentual = 150 WHERE id = $1", produto_id
            )
        await conn.execute(
            "UPDATE produto SET desconto_percentual = 15.5 WHERE id = $1", produto_id
        )
        valor = await conn.fetchval(
            "SELECT desconto_percentual FROM produto WHERE id = $1", produto_id
        )
        assert valor == Decimal("15.50")
    finally:
        # Garante que o schema volta ao estado esperado pelo resto da suíte
        # mesmo se uma asserção acima falhar no meio do teste.
        if await conn.fetchval(_QUERY_COLUNA_EXISTE) is None:
            await conn.execute(_up_sql())
        await conn.close()


async def _autenticar(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/auth/login", json={"email": "admin@amactive.dev", "senha": "amactive123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_produto_sem_desconto_expoe_preco_promocional_null(test_engine) -> None:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def _override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await _autenticar(client)

            produto_resp = await client.post(
                "/produtos",
                json={"nome": "Legging Sem Promoção", "marca": "AMACTIVE"},
                headers=headers,
            )
            assert produto_resp.status_code == 201, produto_resp.text
            assert produto_resp.json()["desconto_percentual"] is None
            produto_id = produto_resp.json()["id"]

            variante_resp = await client.post(
                f"/produtos/{produto_id}/variantes",
                json={"tamanho": "M", "cor": "Preto", "preco_venda": "99.90"},
                headers=headers,
            )
            assert variante_resp.status_code == 201, variante_resp.text
            variante = variante_resp.json()
            assert variante["desconto_percentual"] is None
            assert variante["preco_promocional"] is None

            obter_resp = await client.get(f"/variantes/{variante['id']}", headers=headers)
            assert obter_resp.status_code == 200, obter_resp.text
            assert obter_resp.json()["preco_promocional"] is None
    finally:
        app.dependency_overrides.clear()


async def test_produto_com_desconto_calcula_preco_promocional_na_variante(test_engine) -> None:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def _override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await _autenticar(client)

            produto_resp = await client.post(
                "/produtos",
                json={
                    "nome": "Legging Com Promoção",
                    "marca": "AMACTIVE",
                    "desconto_percentual": "15.00",
                },
                headers=headers,
            )
            assert produto_resp.status_code == 201, produto_resp.text
            assert produto_resp.json()["desconto_percentual"] == "15.00"
            produto_id = produto_resp.json()["id"]

            variante_resp = await client.post(
                f"/produtos/{produto_id}/variantes",
                json={"tamanho": "M", "cor": "Preto", "preco_venda": "99.90"},
                headers=headers,
            )
            assert variante_resp.status_code == 201, variante_resp.text
            variante = variante_resp.json()
            # 99.90 * 0.85 = 84.915 -> ROUND_HALF_UP -> 84.92
            assert variante["desconto_percentual"] == "15.00"
            assert variante["preco_promocional"] == "84.92"

            # Também exposto na busca por SKU (via GET /variantes/{id}, usado
            # pelo PDV) e na listagem de variantes do produto.
            obter_resp = await client.get(f"/variantes/{variante['id']}", headers=headers)
            assert obter_resp.status_code == 200, obter_resp.text
            assert obter_resp.json()["preco_promocional"] == "84.92"

            listar_resp = await client.get(f"/produtos/{produto_id}/variantes", headers=headers)
            assert listar_resp.status_code == 200, listar_resp.text
            assert listar_resp.json()["data"][0]["preco_promocional"] == "84.92"

            detalhe_resp = await client.get(f"/produtos/{produto_id}", headers=headers)
            assert detalhe_resp.status_code == 200, detalhe_resp.text
            assert detalhe_resp.json()["variantes"][0]["preco_promocional"] == "84.92"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("desconto_invalido", ["0.00", "-5.00", "100.01", "150.00"])
async def test_desconto_percentual_fora_do_range_e_rejeitado(
    test_engine, desconto_invalido: str
) -> None:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def _override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await _autenticar(client)

            produto_resp = await client.post(
                "/produtos",
                json={
                    "nome": "Produto Desconto Inválido",
                    "marca": "AMACTIVE",
                    "desconto_percentual": desconto_invalido,
                },
                headers=headers,
            )
            assert produto_resp.status_code == 422, produto_resp.text
    finally:
        app.dependency_overrides.clear()
