"""Configura (cria ou rotaciona) a credencial da Nuvemshop em
`credencial_canal` — ver docs/design-integracao-nuvemshop.md §7.2.

O app privado da Nuvemshop usa um token permanente de altíssimo privilégio
(avaliação §1.1/§1.6) — nunca pode ficar em texto puro em repouso. Este
script cifra `access_token`/`client_secret` via `pgp_sym_encrypt`
(`pgcrypto`, extensão já habilitada desde `migrations/000001_initial_schema`
— nenhuma dependência Python de criptografia nova é introduzida). A chave de
cifragem nunca é armazenada no banco, só existe como variável de ambiente do
processo que cifra/decifra.

Nota de escopo (deliberada): `CREDENCIAL_CANAL_ENCRYPTION_KEY` é a mesma
variável que o passo 5 (`client.py`/`CredencialCanalRepository`) vai
adicionar a `Settings` em `core/config.py` (mesmo padrão de `jwt_secret`,
incluindo a validação `_rejeita_segredo_padrao_fora_de_dev`). Este script,
porém, não depende de `Settings` para ela — lê diretamente de
`os.environ`, assim como `STORE_ID`/`NUVEMSHOP_ACCESS_TOKEN`/
`NUVEMSHOP_CLIENT_SECRET` — porque não há necessidade real de reutilizar
`Settings` aqui (o script roda uma vez, fora do processo da API/worker) e
mexer em `core/config.py` é explicitamente escopo do passo 5, não deste.

Idempotente/re-executável — serve tanto para a configuração inicial quanto
para rotação de credencial (`INSERT ... ON CONFLICT (canal) DO UPDATE`).
`canal` é sempre `'NUVEMSHOP'` (única credencial suportada na Fase 1).

Segurança: o token/secret em texto puro nunca é logado (nem em `print`, nem
em mensagem de exceção) — só trafega como bind parameter (`$1`/`$2`/...)
para `pgp_sym_encrypt`, nunca interpolado na string SQL.

Uso (uma única vez ou a cada rotação, por `kubectl exec` no pod da API — ver
infra/README.md):
    STORE_ID=123456 \
    NUVEMSHOP_ACCESS_TOKEN='<token-permanente-do-app-privado>' \
    NUVEMSHOP_CLIENT_SECRET='<client-secret-do-app-privado>' \
    CREDENCIAL_CANAL_ENCRYPTION_KEY='<chave-forte-de-cifragem>' \
    python -m amactive.scripts.configurar_credencial_nuvemshop
"""

from __future__ import annotations

import asyncio
import os
import sys

import asyncpg

from amactive.core.config import settings


def _asyncpg_dsn(database_url: str) -> str:
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _ler_variaveis_obrigatorias() -> tuple[str, str, str, str]:
    store_id = os.environ.get("STORE_ID")
    access_token = os.environ.get("NUVEMSHOP_ACCESS_TOKEN")
    client_secret = os.environ.get("NUVEMSHOP_CLIENT_SECRET")
    chave = os.environ.get("CREDENCIAL_CANAL_ENCRYPTION_KEY")

    faltando = [
        nome
        for nome, valor in (
            ("STORE_ID", store_id),
            ("NUVEMSHOP_ACCESS_TOKEN", access_token),
            ("NUVEMSHOP_CLIENT_SECRET", client_secret),
            ("CREDENCIAL_CANAL_ENCRYPTION_KEY", chave),
        )
        if not valor
    ]
    if faltando:
        raise SystemExit(
            "Variáveis de ambiente obrigatórias ausentes (sem defaults — nunca "
            f"configurar credencial de canal com valor previsível): {', '.join(faltando)}."
        )

    # mypy: os valores acima já foram validados como não vazios.
    assert store_id and access_token and client_secret and chave
    return store_id, access_token, client_secret, chave


async def configurar_credencial_nuvemshop() -> None:
    store_id, access_token, client_secret, chave = _ler_variaveis_obrigatorias()

    conn = await asyncpg.connect(dsn=_asyncpg_dsn(settings.database_url))
    try:
        try:
            await conn.execute(
                """
                INSERT INTO credencial_canal
                    (canal, store_id, access_token_cifrado, client_secret_cifrado)
                VALUES ('NUVEMSHOP', $1, pgp_sym_encrypt($2, $4), pgp_sym_encrypt($3, $4))
                ON CONFLICT (canal) DO UPDATE SET
                    store_id = EXCLUDED.store_id,
                    access_token_cifrado = EXCLUDED.access_token_cifrado,
                    client_secret_cifrado = EXCLUDED.client_secret_cifrado,
                    atualizado_em = now()
                """,
                store_id,
                access_token,
                client_secret,
                chave,
            )
        except asyncpg.PostgresError as exc:
            # `str(exc)` aqui é seguro: o erro vem do protocolo do Postgres
            # sobre a query (que só contém `$1..$4`, nunca os valores em si,
            # enviados fora de banda como bind parameters) — nunca inclui o
            # token/secret em texto puro.
            raise SystemExit(f"Falha ao gravar credencial cifrada no banco: {exc}") from exc

        linha = await conn.fetchrow(
            """
            SELECT store_id, criado_em, atualizado_em
            FROM credencial_canal
            WHERE canal = 'NUVEMSHOP'
            """
        )
        if linha is None:
            # Não deveria acontecer logo após o upsert acima — defensivo.
            raise SystemExit("Credencial não encontrada após a gravação — estado inesperado.")

        print(
            f"[ok] credencial NUVEMSHOP configurada/rotacionada: store_id={linha['store_id']}, "
            f"criado_em={linha['criado_em']}, atualizado_em={linha['atualizado_em']} "
            "(access_token/client_secret cifrados em repouso — nunca impressos)."
        )
    finally:
        await conn.close()


def main() -> None:
    try:
        asyncio.run(configurar_credencial_nuvemshop())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Falha ao configurar credencial da Nuvemshop: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
