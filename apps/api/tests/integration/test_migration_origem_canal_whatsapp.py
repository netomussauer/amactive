"""Testes de integração da migration `000006_origem_canal_whatsapp` contra um
Postgres real: `ADD VALUE` sobre um schema com dados (up), idempotência, e o
rollback documentado em `.down.sql` (recria o tipo sem 'WHATSAPP' quando nenhuma
linha o usa; aborta com erro claro quando alguma usa).

Diferente de `test_migration_desconto_promocional.py`, este teste NÃO mexe no
banco compartilhado de testes: o `.down.sql` recria o tipo `origem_canal_pedido`
(novo OID), o que poderia invalidar caches de tipos das conexões do pool dos
demais testes. Por isso cada teste roda em um banco descartável, criado a
partir das migrations reais (000001 e 000003-000005; a 000002 é seed de dev e
não é necessária) e removido ao final."""

from __future__ import annotations

import os
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio

pytestmark = pytest.mark.integration

_TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://amactive:amactive@localhost:5432/amactive_test"
)
_ROTULOS_SEM_WHATSAPP = ["PDV", "NUVEMSHOP"]
_ROTULOS_COM_WHATSAPP = ["PDV", "NUVEMSHOP", "WHATSAPP"]


def _dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _sql(nome: str) -> str:
    # Resolvido sob demanda (não em import time) — ver `conftest._migrations_dir`.
    return (Path(__file__).resolve().parents[4] / "migrations" / nome).read_text(encoding="utf-8")


@pytest_asyncio.fixture
async def conn() -> AsyncGenerator[asyncpg.Connection, None]:
    base_dsn, _, _ = _dsn(_TEST_DATABASE_URL).rpartition("/")
    dbname = f"amactive_mig6_{uuid.uuid4().hex[:8]}"
    admin = await asyncpg.connect(dsn=f"{base_dsn}/postgres")
    try:
        await admin.execute(f'CREATE DATABASE "{dbname}"')
        # Sem cache de prepared statements: o `.down.sql` recria o tipo (novo OID) e
        # um statement preparado antes dele falharia com "cache lookup failed for
        # type" — o mesmo efeito que o down tem sobre conexões longevas da API.
        conexao = await asyncpg.connect(dsn=f"{base_dsn}/{dbname}", statement_cache_size=0)
        try:
            for nome in (
                "000001_initial_schema.up.sql",
                "000003_produto_imagem.up.sql",
                "000004_produto_desconto_promocional.up.sql",
                "000005_integracao_nuvemshop.up.sql",
            ):
                await conexao.execute(_sql(nome))
            yield conexao
        finally:
            await conexao.close()
    finally:
        await admin.execute(f'DROP DATABASE IF EXISTS "{dbname}" WITH (FORCE)')
        await admin.close()


async def _rotulos(conn: asyncpg.Connection) -> list[str]:
    linhas = await conn.fetch(
        """
        SELECT e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
        WHERE t.typname = 'origem_canal_pedido' ORDER BY e.enumsortorder
        """
    )
    return [linha["enumlabel"] for linha in linhas]


async def _criar_usuario(conn: asyncpg.Connection) -> uuid.UUID:
    return await conn.fetchval(
        """
        INSERT INTO usuario (nome, email, senha_hash)
        VALUES ('Teste Migration', $1, 'hash') RETURNING id
        """,
        f"mig-{uuid.uuid4().hex[:8]}@amactive.dev",
    )


async def _criar_pedido(
    conn: asyncpg.Connection,
    usuario_id: uuid.UUID,
    origem: str | None,
    externo: str | None = None,
) -> None:
    numero = f"M-{uuid.uuid4().hex[:10]}"
    if origem is None:  # exercita o DEFAULT da coluna
        await conn.execute(
            """
            INSERT INTO pedido (numero, usuario_id, status, subtotal, valor_total, pedido_externo_id)
            VALUES ($1, $2, 'CONFIRMADO', 10, 10, $3)
            """,
            numero,
            usuario_id,
            externo,
        )
        return
    await conn.execute(
        """
        INSERT INTO pedido (numero, usuario_id, status, subtotal, valor_total,
                            origem_canal, pedido_externo_id)
        VALUES ($1, $2, 'CONFIRMADO', 10, 10, $3::origem_canal_pedido, $4)
        """,
        numero,
        usuario_id,
        origem,
        externo,
    )


async def _contagem_por_origem(conn: asyncpg.Connection) -> dict[str, int]:
    linhas = await conn.fetch(
        "SELECT origem_canal::text AS origem, count(*) AS total FROM pedido GROUP BY 1"
    )
    return {linha["origem"]: linha["total"] for linha in linhas}


async def test_up_adiciona_whatsapp_preservando_dados_e_indices_valem_para_o_novo_canal(
    conn: asyncpg.Connection,
) -> None:
    usuario_id = await _criar_usuario(conn)
    await _criar_pedido(conn, usuario_id, None)
    await _criar_pedido(conn, usuario_id, "NUVEMSHOP", "1001")
    assert await _rotulos(conn) == _ROTULOS_SEM_WHATSAPP

    await conn.execute(_sql("000006_origem_canal_whatsapp.up.sql"))

    assert await _rotulos(conn) == _ROTULOS_COM_WHATSAPP
    assert await _contagem_por_origem(conn) == {"PDV": 1, "NUVEMSHOP": 1}

    # Escopo do ÍNDICE (schema): único por (origem, número). A API só aceita número
    # externo em pedidos NUVEMSHOP; aqui exercitamos o índice diretamente.
    await _criar_pedido(conn, usuario_id, "WHATSAPP", "1001")  # mesmo número, outra origem: ok
    await _criar_pedido(conn, usuario_id, "WHATSAPP")  # sem número: ok, várias vezes
    await _criar_pedido(conn, usuario_id, "WHATSAPP")
    with pytest.raises(asyncpg.UniqueViolationError) as duplicado:
        await _criar_pedido(conn, usuario_id, "WHATSAPP", "1001")
    assert duplicado.value.constraint_name == "uq_pedido_origem_canal_externo"

    # Reaplicar é inofensivo (ADD VALUE IF NOT EXISTS).
    await conn.execute(_sql("000006_origem_canal_whatsapp.up.sql"))
    assert await _rotulos(conn) == _ROTULOS_COM_WHATSAPP


async def test_down_aborta_enquanto_existir_pedido_whatsapp_e_nao_altera_nada(
    conn: asyncpg.Connection,
) -> None:
    usuario_id = await _criar_usuario(conn)
    await conn.execute(_sql("000006_origem_canal_whatsapp.up.sql"))
    await _criar_pedido(conn, usuario_id, "WHATSAPP", "77")

    with pytest.raises(asyncpg.RaiseError, match="Rollback 000006 abortado"):
        await conn.execute(_sql("000006_origem_canal_whatsapp.down.sql"))
    # O script tem BEGIN explícito: como no psql, a transação fica abortada até o ROLLBACK.
    await conn.execute("ROLLBACK")

    assert await _rotulos(conn) == _ROTULOS_COM_WHATSAPP
    assert await _contagem_por_origem(conn) == {"WHATSAPP": 1}


async def test_down_recria_o_tipo_sem_whatsapp_e_ciclo_up_down_up_e_reversivel(
    conn: asyncpg.Connection,
) -> None:
    usuario_id = await _criar_usuario(conn)
    await _criar_pedido(conn, usuario_id, None)
    await _criar_pedido(conn, usuario_id, "NUVEMSHOP", "2002")
    await conn.execute(_sql("000006_origem_canal_whatsapp.up.sql"))
    await _criar_pedido(conn, usuario_id, "WHATSAPP", "3003")
    await conn.execute("DELETE FROM pedido WHERE origem_canal::text = 'WHATSAPP'")

    await conn.execute(_sql("000006_origem_canal_whatsapp.down.sql"))

    assert await _rotulos(conn) == _ROTULOS_SEM_WHATSAPP
    assert await _contagem_por_origem(conn) == {"PDV": 1, "NUVEMSHOP": 1}
    with pytest.raises(asyncpg.InvalidTextRepresentationError):
        await _criar_pedido(conn, usuario_id, "WHATSAPP")
    # DEFAULT 'PDV' e índices da 000005 restaurados.
    await _criar_pedido(conn, usuario_id, None)
    assert (await _contagem_por_origem(conn))["PDV"] == 2
    definicoes = {
        linha["indexname"]: linha["indexdef"]
        for linha in await conn.fetch(
            "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'pedido'"
        )
    }
    assert "UNIQUE" in definicoes["uq_pedido_origem_canal_externo"]
    assert "pedido_externo_id IS NOT NULL" in definicoes["uq_pedido_origem_canal_externo"]
    assert "idx_pedido_origem_canal" in definicoes
    with pytest.raises(asyncpg.UniqueViolationError):
        await _criar_pedido(conn, usuario_id, "NUVEMSHOP", "2002")

    # Down repetido não quebra (idempotente); up volta a funcionar.
    await conn.execute(_sql("000006_origem_canal_whatsapp.down.sql"))
    assert await _rotulos(conn) == _ROTULOS_SEM_WHATSAPP
    await conn.execute(_sql("000006_origem_canal_whatsapp.up.sql"))
    assert await _rotulos(conn) == _ROTULOS_COM_WHATSAPP
    await _criar_pedido(conn, usuario_id, "WHATSAPP", "3003")
