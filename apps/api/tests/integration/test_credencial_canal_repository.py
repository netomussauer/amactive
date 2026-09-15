"""Teste de integração de `SqlAlchemyCredencialCanalRepository` — decifra
`credencial_canal` via `pgp_sym_decrypt` (pgcrypto), ver
docs/design-integracao-nuvemshop.md §7.2."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao
from amactive.contexts.integracao_canais.infrastructure.persistence.repositories import (
    SqlAlchemyCredencialCanalRepository,
)
from amactive.core.config import settings

pytestmark = pytest.mark.integration


async def _inserir_credencial_cifrada(
    db_session: AsyncSession, *, store_id: str, access_token: str, client_secret: str
) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO credencial_canal
                (id, canal, store_id, access_token_cifrado, client_secret_cifrado)
            VALUES
                (:id, 'NUVEMSHOP', :store_id,
                 pgp_sym_encrypt(:access_token, :chave),
                 pgp_sym_encrypt(:client_secret, :chave))
            """
        ),
        {
            "id": uuid.uuid4(),
            "store_id": store_id,
            "access_token": access_token,
            "client_secret": client_secret,
            "chave": settings.credencial_canal_encryption_key,
        },
    )
    await db_session.commit()


async def test_buscar_token_decifrado_retorna_credencial_decifrada(
    db_session: AsyncSession,
) -> None:
    await _inserir_credencial_cifrada(
        db_session,
        store_id="123456",
        access_token="token-permanente-do-app-privado",
        client_secret="client-secret-do-app-privado",
    )
    repo = SqlAlchemyCredencialCanalRepository(db_session)

    credencial = await repo.buscar_token_decifrado(CanalIntegracao.NUVEMSHOP)

    assert credencial is not None
    assert credencial.canal == CanalIntegracao.NUVEMSHOP
    assert credencial.store_id == "123456"
    assert credencial.access_token == "token-permanente-do-app-privado"
    assert credencial.client_secret == "client-secret-do-app-privado"


async def test_buscar_token_decifrado_retorna_none_quando_nao_configurado(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyCredencialCanalRepository(db_session)

    credencial = await repo.buscar_token_decifrado(CanalIntegracao.NUVEMSHOP)

    assert credencial is None
