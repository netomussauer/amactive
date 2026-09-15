"""Teste de integração ponta a ponta via HTTP (ASGI in-process) do endpoint
`POST /integracoes/nuvemshop/webhooks` — ver docs/design-integracao-nuvemshop.md
§5.1/§9 item 6.

A dependency `get_db_session` é sobrescrita para reutilizar a MESMA
`db_session` (fixture transacional por SAVEPOINT, ver
tests/integration/conftest.py) usada para inserir a credencial de teste —
diferente de tests/integration/test_api_fluxo_completo.py (que usa uma
`AsyncSession` nova por request, ligada diretamente a `test_engine`), aqui
tudo roda na mesma transação de teste para que o `INSERT` de
`credencial_canal` feito no teste seja visível ao handler HTTP sem precisar
de commit real no banco (e sem sujar o banco entre execuções)."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.core.config import settings
from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration

_CLIENT_SECRET_TESTE = "segredo-hmac-de-teste"


async def _inserir_credencial_canal(
    db_session: AsyncSession, *, client_secret: str = _CLIENT_SECRET_TESTE
) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO credencial_canal
                (id, canal, store_id, access_token_cifrado, client_secret_cifrado)
            VALUES
                (:id, 'NUVEMSHOP', 'store-teste',
                 pgp_sym_encrypt('token-teste', :chave),
                 pgp_sym_encrypt(:client_secret, :chave))
            """
        ),
        {
            "id": uuid.uuid4(),
            "client_secret": client_secret,
            "chave": settings.credencial_canal_encryption_key,
        },
    )
    await db_session.commit()


def _assinar(corpo: bytes, *, client_secret: str = _CLIENT_SECRET_TESTE) -> str:
    return hmac.new(client_secret.encode("utf-8"), corpo, hashlib.sha256).hexdigest()


async def _post_webhook(db_session: AsyncSession, *, corpo: bytes, assinatura: str):
    async def _override_get_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/integracoes/nuvemshop/webhooks",
                content=corpo,
                headers={
                    "content-type": "application/json",
                    "x-linkedstore-hmac-sha256": assinatura,
                },
            )
    finally:
        app.dependency_overrides.clear()


async def test_webhook_valido_e_registrado_e_responde_200(db_session: AsyncSession) -> None:
    await _inserir_credencial_canal(db_session)
    payload = {"store_id": "store-teste", "event": "order/paid", "id": 555000111}
    corpo = json.dumps(payload).encode("utf-8")

    resposta = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))

    assert resposta.status_code == 200, resposta.text

    resultado = await db_session.execute(
        text(
            "SELECT status, tipo_evento, id_recurso_externo, payload_bruto "
            "FROM webhook_evento WHERE evento_externo_id = :evento_externo_id"
        ),
        {"evento_externo_id": "NUVEMSHOP:order/paid:555000111"},
    )
    linha = resultado.mappings().one()
    assert linha["status"] == "PENDENTE"
    assert linha["tipo_evento"] == "order/paid"
    assert linha["id_recurso_externo"] == "555000111"
    assert linha["payload_bruto"] == payload


async def test_webhook_com_assinatura_invalida_retorna_401_sem_gravar_evento(
    db_session: AsyncSession,
) -> None:
    await _inserir_credencial_canal(db_session)
    payload = {"store_id": "store-teste", "event": "order/paid", "id": 999999}
    corpo = json.dumps(payload).encode("utf-8")

    resposta = await _post_webhook(db_session, corpo=corpo, assinatura="assinatura-forjada")

    assert resposta.status_code == 401

    total = await db_session.scalar(
        text("SELECT count(*) FROM webhook_evento WHERE id_recurso_externo = '999999'")
    )
    assert total == 0


async def test_webhook_entregue_duas_vezes_e_idempotente_apenas_um_registro(
    db_session: AsyncSession,
) -> None:
    await _inserir_credencial_canal(db_session)
    payload = {"store_id": "store-teste", "event": "order/paid", "id": 777000111}
    corpo = json.dumps(payload).encode("utf-8")
    assinatura = _assinar(corpo)

    primeira_resposta = await _post_webhook(db_session, corpo=corpo, assinatura=assinatura)
    segunda_resposta = await _post_webhook(db_session, corpo=corpo, assinatura=assinatura)

    # A Nuvemshop declara explicitamente que entregas duplicadas podem
    # ocorrer (avaliação §1.4) — o controller responde 200 nos dois casos
    # (design §5.1 passo 6), mas nunca cria um segundo registro (design
    # §5.2: `UNIQUE(evento_externo_id)`).
    assert primeira_resposta.status_code == 200
    assert segunda_resposta.status_code == 200

    total = await db_session.scalar(
        text(
            "SELECT count(*) FROM webhook_evento "
            "WHERE evento_externo_id = 'NUVEMSHOP:order/paid:777000111'"
        )
    )
    assert total == 1
