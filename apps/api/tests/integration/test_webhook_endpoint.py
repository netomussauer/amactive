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
from prometheus_client import REGISTRY
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.integracao_canais.infrastructure.api.router import (
    limpar_cache_credencial,
)
from amactive.core.config import settings
from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration

_CLIENT_SECRET_TESTE = "segredo-hmac-de-teste"


@pytest.fixture(autouse=True)
def _limpar_cache_credencial_do_router() -> None:
    # O router cacheia a credencial por 30s (proteção contra flood anônimo);
    # cada teste insere a sua própria em uma transação isolada.
    limpar_cache_credencial()


async def _inserir_credencial_canal(
    db_session: AsyncSession,
    *,
    client_secret: str = _CLIENT_SECRET_TESTE,
    store_id: str = "store-teste",
) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO credencial_canal
                (id, canal, store_id, access_token_cifrado, client_secret_cifrado)
            VALUES
                (:id, 'NUVEMSHOP', :store_id,
                 pgp_sym_encrypt('token-teste', :chave),
                 pgp_sym_encrypt(:client_secret, :chave))
            """
        ),
        {
            "id": uuid.uuid4(),
            "store_id": store_id,
            "client_secret": client_secret,
            "chave": settings.credencial_canal_encryption_key,
        },
    )
    await db_session.commit()


def _assinar(corpo: bytes, *, client_secret: str = _CLIENT_SECRET_TESTE) -> str:
    return hmac.new(client_secret.encode("utf-8"), corpo, hashlib.sha256).hexdigest()


async def _post_webhook(db_session: AsyncSession, *, corpo: bytes, assinatura: str | bytes):
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
    antes_metrica = (
        REGISTRY.get_sample_value("webhook_evento_recebido_total", {"tipo_evento": "order/paid"})
        or 0.0
    )

    resposta = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))

    assert resposta.status_code == 200, resposta.text

    # Métrica `webhook_evento_recebido_total{tipo_evento}` (design §8) —
    # incrementada no controller (`infrastructure/api/router.py`) para todo
    # webhook autenticado.
    depois_metrica = REGISTRY.get_sample_value(
        "webhook_evento_recebido_total", {"tipo_evento": "order/paid"}
    )
    assert depois_metrica == antes_metrica + 1

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


async def test_webhook_com_store_id_numerico_como_a_nuvemshop_envia_e_registrado(
    db_session: AsyncSession,
) -> None:
    # A Nuvemshop envia `store_id` como NÚMERO no JSON; `credencial_canal.
    # store_id` é texto. Regressão: com `store_id: str` estrito o Pydantic v2
    # rejeitava int e todo webhook real virava 500.
    await _inserir_credencial_canal(db_session, store_id="123456")
    payload = {"store_id": 123456, "event": "order/paid", "id": 880000111}
    corpo = json.dumps(payload).encode("utf-8")

    resposta = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))

    assert resposta.status_code == 200, resposta.text
    total = await db_session.scalar(
        text(
            "SELECT count(*) FROM webhook_evento "
            "WHERE evento_externo_id = 'NUVEMSHOP:order/paid:880000111'"
        )
    )
    assert total == 1


async def test_webhook_de_outra_loja_com_hmac_valido_retorna_401_sem_gravar_evento(
    db_session: AsyncSession,
) -> None:
    await _inserir_credencial_canal(db_session, store_id="123456")
    payload = {"store_id": 999999, "event": "order/paid", "id": 880000222}
    corpo = json.dumps(payload).encode("utf-8")

    resposta = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))

    assert resposta.status_code == 401
    total = await db_session.scalar(
        text("SELECT count(*) FROM webhook_evento WHERE id_recurso_externo = '880000222'")
    )
    assert total == 0


async def test_webhook_sem_credencial_configurada_retorna_401_generico_e_nao_404(
    db_session: AsyncSession,
) -> None:
    # Endpoint anônimo: não pode revelar que a integração não está
    # configurada (um 404 com detalhe seria distinguível do 401 de
    # assinatura inválida).
    corpo = json.dumps({"store_id": "x", "event": "order/paid", "id": 1}).encode("utf-8")

    resposta = await _post_webhook(db_session, corpo=corpo, assinatura="qualquer")

    assert resposta.status_code == 401
    assert "credencial" not in resposta.text.lower()
    assert "NUVEMSHOP" not in resposta.text


@pytest.mark.parametrize(
    "corpo",
    [
        b"isto nao e json",
        b'["lista", "em", "vez", "de", "objeto"]',
        b'{"store_id": "store-teste", "event": "order/paid"}',
        b'{"store_id": "store-teste", "event": "order/paid", "id": "nao-numerico"}',
    ],
)
async def test_webhook_autenticado_com_corpo_invalido_retorna_422_e_nao_500(
    db_session: AsyncSession, corpo: bytes
) -> None:
    await _inserir_credencial_canal(db_session)

    resposta = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))

    assert resposta.status_code == 422, resposta.text


async def test_webhook_com_tipo_de_evento_acima_de_50_caracteres_retorna_422(
    db_session: AsyncSession,
) -> None:
    # `webhook_evento.tipo_evento` é varchar(50) — sem o limite no schema o
    # INSERT estouraria em 500.
    await _inserir_credencial_canal(db_session)
    payload = {"store_id": "store-teste", "event": "x" * 51, "id": 880000333}
    corpo = json.dumps(payload).encode("utf-8")

    resposta = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))

    assert resposta.status_code == 422


async def test_webhook_com_assinatura_nao_ascii_retorna_401_e_nao_500(
    db_session: AsyncSession,
) -> None:
    await _inserir_credencial_canal(db_session)
    corpo = json.dumps({"store_id": "store-teste", "event": "order/paid", "id": 1}).encode("utf-8")

    # httpx só aceita `str` ASCII em headers; na rede o valor chega como
    # bytes (o Starlette os decodifica como latin-1).
    resposta = await _post_webhook(
        db_session, corpo=corpo, assinatura="assinatura-é-ã".encode("latin-1")
    )

    assert resposta.status_code == 401


async def test_credencial_e_cacheada_requisicoes_seguintes_nao_consultam_o_banco(
    db_session: AsyncSession,
) -> None:
    await _inserir_credencial_canal(db_session)
    payload = {"store_id": "store-teste", "event": "order/paid", "id": 880000444}
    corpo = json.dumps(payload).encode("utf-8")

    primeira = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))
    assert primeira.status_code == 200

    # Remove a credencial do banco: dentro do TTL do cache, o handler não
    # precisa mais consultá-la (um flood anônimo não gera queries).
    await db_session.execute(text("DELETE FROM credencial_canal"))
    await db_session.commit()

    segunda = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))
    assert segunda.status_code == 200

    limpar_cache_credencial()
    terceira = await _post_webhook(db_session, corpo=corpo, assinatura=_assinar(corpo))
    assert terceira.status_code == 401
