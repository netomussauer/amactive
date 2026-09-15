"""Cria o usuário de sistema que "assina" pedidos importados da Nuvemshop —
resolve o gap de `usuario_id` (`NOT NULL` em `pedido`/`movimentacao_estoque`)
descrito em docs/design-integracao-nuvemshop.md §3.1: um pedido criado pelo
worker de webhook não tem um operador humano por trás, e o design escolhe
deliberadamente **não** tornar `usuario_id` nullable (isso enfraqueceria a
auditoria do caso comum, o PDV) — em vez disso, um usuário seedado assina
esses pedidos.

E-mail fixo e bem-conhecido (`integracao.nuvemshop@sistema.amactive.internal`):
o worker resolve o `id` deste usuário por e-mail uma vez no startup e mantém
em cache de processo — nunca hardcoda um UUID, que mudaria entre ambientes
(dev/staging/prod geram UUIDs diferentes via `gen_random_uuid()`).

`ativo = false` de propósito — este usuário nunca deve logar. É defesa em
profundidade mesmo que a senha (gerada aleatoriamente abaixo, nunca impressa
nem lida de env var) vazasse: `get_current_user` rejeita usuários inativos.
Irrelevante para o caminho real de uso deste usuário, que é uma chamada
direta a `CriarPedidoUseCase` pelo worker — nunca passa por
`get_current_user`/login.

Idempotente e seguro de deixar na imagem permanentemente: se já existir um
usuário com o e-mail acima, não faz nada (`[skip]`).

Uso (uma única vez, por `kubectl exec` no pod da API — ver infra/README.md):
    python -m amactive.scripts.bootstrap_usuario_integracao
"""

from __future__ import annotations

import asyncio
import secrets
import sys
import uuid
from datetime import UTC, datetime

import asyncpg

from amactive.core.config import settings
from amactive.core.security import hash_senha

EMAIL_USUARIO_INTEGRACAO = "integracao.nuvemshop@sistema.amactive.internal"
NOME_USUARIO_INTEGRACAO = "Integração Nuvemshop (sistema)"


def _asyncpg_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def bootstrap_usuario_integracao() -> None:
    conn = await asyncpg.connect(dsn=_asyncpg_dsn(settings.database_url))
    try:
        ja_existe = await conn.fetchval(
            "SELECT 1 FROM usuario WHERE email = $1", EMAIL_USUARIO_INTEGRACAO
        )
        if ja_existe:
            print(
                f"[skip] usuário de integração '{EMAIL_USUARIO_INTEGRACAO}' já existe — "
                "nada a fazer (script seguro para rodar de novo, não duplica)."
            )
            return

        # Senha aleatória forte gerada internamente — nunca lida de env var
        # nem impressa: ninguém precisa efetivamente logar com este usuário,
        # e `ativo=false` já impede login mesmo que ela vazasse. Pedir uma
        # env var tipo `BOOTSTRAP_USUARIO_INTEGRACAO_SENHA` seria security
        # theater desnecessário para um usuário que nunca loga.
        senha_aleatoria = secrets.token_urlsafe(32)

        await conn.execute(
            """
            INSERT INTO usuario (id, nome, email, senha_hash, papel, ativo, criado_em)
            VALUES ($1, $2, $3, $4, 'VENDEDOR', false, $5)
            """,
            uuid.uuid4(),
            NOME_USUARIO_INTEGRACAO,
            EMAIL_USUARIO_INTEGRACAO,
            hash_senha(senha_aleatoria),
            datetime.now(UTC),
        )
        print(
            f"[ok] usuário de integração '{EMAIL_USUARIO_INTEGRACAO}' criado "
            "(papel=VENDEDOR, ativo=false — nunca loga, só assina pedidos via "
            "chamada direta ao caso de uso)."
        )
    finally:
        await conn.close()


def main() -> None:
    try:
        asyncio.run(bootstrap_usuario_integracao())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Falha ao criar usuário de integração: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
