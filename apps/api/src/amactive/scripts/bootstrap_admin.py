"""Cria o primeiro usuário ADMIN de um ambiente que ainda não tem nenhum
usuário — resolve o problema de "ovo e galinha" de implantações que não
usam a migration de seed de desenvolvimento (`000002_seed_dev.up.sql`,
propositalmente excluída de ambientes reais por criar um ADMIN com senha
fraca conhecida — ver infra/k8s/api/migrations-configmap.yaml).

Sem nenhum usuário na tabela `usuario`, ninguém consegue fazer login, e
`POST /usuarios` (criar usuário) exige ser ADMIN — não há como sair desse
estado pela API. Este script existe só para esse bootstrap inicial.

Idempotente e seguro de deixar na imagem permanentemente: só insere um
usuário se a tabela `usuario` estiver vazia (nenhum outro ambiente é
afetado, rodar de novo depois que já existe gente cadastrada é um no-op).

Uso (uma única vez, por `kubectl exec` no pod da API — ver infra/README.md):
    BOOTSTRAP_ADMIN_EMAIL=admin@amactive.dev \
    BOOTSTRAP_ADMIN_SENHA='<senha-forte-aqui>' \
    BOOTSTRAP_ADMIN_NOME='Administrador AMACTIVE' \
    python -m amactive.scripts.bootstrap_admin
"""

from __future__ import annotations

import asyncio
import os
import sys
import uuid
from datetime import UTC, datetime

import asyncpg

from amactive.core.config import settings
from amactive.core.security import hash_senha


def _asyncpg_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _ler_variaveis_obrigatorias() -> tuple[str, str, str]:
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL")
    senha = os.environ.get("BOOTSTRAP_ADMIN_SENHA")
    nome = os.environ.get("BOOTSTRAP_ADMIN_NOME", "Administrador")
    if not email or not senha:
        raise SystemExit(
            "BOOTSTRAP_ADMIN_EMAIL e BOOTSTRAP_ADMIN_SENHA são obrigatórias "
            "(sem defaults — nunca criar um admin com senha previsível)."
        )
    if len(senha) < 8:
        raise SystemExit("BOOTSTRAP_ADMIN_SENHA precisa ter ao menos 8 caracteres.")
    return email, senha, nome


async def bootstrap_admin() -> None:
    email, senha, nome = _ler_variaveis_obrigatorias()

    conn = await asyncpg.connect(dsn=_asyncpg_dsn(settings.database_url))
    try:
        total_usuarios = await conn.fetchval("SELECT count(*) FROM usuario")
        if total_usuarios > 0:
            print(
                f"[skip] já existem {total_usuarios} usuário(s) cadastrado(s) — "
                "nada a fazer (script seguro para rodar de novo, não duplica)."
            )
            return

        await conn.execute(
            """
            INSERT INTO usuario (id, nome, email, senha_hash, papel, ativo, criado_em)
            VALUES ($1, $2, $3, $4, 'ADMIN', true, $5)
            """,
            uuid.uuid4(),
            nome,
            email,
            hash_senha(senha),
            datetime.now(UTC),
        )
        print(f"[ok] usuário ADMIN '{email}' criado.")
    finally:
        await conn.close()


def main() -> None:
    try:
        asyncio.run(bootstrap_admin())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Falha ao criar admin inicial: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
