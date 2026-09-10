"""Aplicador simples de migrations SQL puro (ver docs/SDD.md ADR-003).

Decisão pendente registrada em docs/SDD.md §7 ("Ferramenta exata de
aplicação de migrations SQL puro — golang-migrate via Makefile vs. script
Python equivalente"): este script cobre a lacuna com a opção mais simples
possível — sem introduzir uma nova dependência de infraestrutura (Go/
golang-migrate) só para rodar `.up.sql` sequenciais localmente.

Comportamento:
  - Lê `migrations/NNNNNN_nome.up.sql` em ordem lexicográfica.
  - Mantém uma tabela `schema_migrations(versao text primary key,
    aplicada_em timestamptz)` para não reaplicar migrations já executadas
    (idempotente — seguro rodar a cada `docker compose up`).
  - NUNCA roda `.down.sql` automaticamente (rollback é sempre uma ação
    manual e explícita do operador).

Uso:
    python -m amactive.scripts.apply_migrations
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import asyncpg

from amactive.core.config import settings


def _asyncpg_dsn(database_url: str) -> str:
    """Converte a URL do SQLAlchemy (`postgresql+asyncpg://...`) para o
    formato aceito diretamente por `asyncpg.connect` (`postgresql://...`)."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _localizar_diretorio_migrations() -> Path:
    """Tenta localizar `migrations/` tanto no layout de container Docker
    (`/app/migrations`, montado via docker-compose) quanto em desenvolvimento
    local rodando a partir de `apps/api` (`../../migrations`, raiz do repo)."""
    candidatos = [
        Path("/app/migrations"),
        Path(__file__).resolve().parents[5] / "migrations",
        Path.cwd() / "migrations",
        Path.cwd().parent.parent / "migrations",
    ]
    for candidato in candidatos:
        if candidato.is_dir():
            return candidato
    raise FileNotFoundError(
        "Não foi possível localizar o diretório migrations/. Defina o layout "
        "esperado (ver docker-compose.yml) ou rode este script a partir da "
        "raiz do repositório."
    )


async def aplicar_migrations() -> None:
    diretorio = _localizar_diretorio_migrations()
    arquivos = sorted(diretorio.glob("*.up.sql"))
    if not arquivos:
        print(f"Nenhuma migration encontrada em {diretorio}.")
        return

    conn = await asyncpg.connect(dsn=_asyncpg_dsn(settings.database_url))
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

        for arquivo in arquivos:
            versao = arquivo.name
            if versao in aplicadas:
                print(f"[skip] {versao} já aplicada.")
                continue

            sql = arquivo.read_text(encoding="utf-8")
            print(f"[apply] {versao} ...")
            await conn.execute(sql)
            await conn.execute("INSERT INTO schema_migrations (versao) VALUES ($1)", versao)
            print(f"[ok] {versao}")
    finally:
        await conn.close()


def main() -> None:
    try:
        asyncio.run(aplicar_migrations())
    except Exception as exc:
        print(f"Falha ao aplicar migrations: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
