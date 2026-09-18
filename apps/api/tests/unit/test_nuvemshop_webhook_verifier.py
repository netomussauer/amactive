"""Testes unitários de `HmacSha256WebhookVerifier` — função pura, sem I/O
(design §5.1)."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from amactive.contexts.integracao_canais.infrastructure.nuvemshop.webhook_verifier import (
    HmacSha256WebhookVerifier,
)

pytestmark = pytest.mark.unit


def _assinar(corpo: bytes, secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), corpo, hashlib.sha256).hexdigest()


def test_verificar_aceita_assinatura_valida() -> None:
    verifier = HmacSha256WebhookVerifier()
    corpo = b'{"store_id": 123, "event": "order/paid", "id": 456}'
    secret = "client-secret-do-app-privado"
    assinatura = _assinar(corpo, secret)

    assert (
        verifier.verificar(corpo_bruto=corpo, assinatura=assinatura, client_secret=secret) is True
    )


def test_verificar_rejeita_assinatura_de_secret_diferente() -> None:
    verifier = HmacSha256WebhookVerifier()
    corpo = b'{"store_id": 123, "event": "order/paid", "id": 456}'
    assinatura = _assinar(corpo, "secret-errado")

    resultado = verifier.verificar(
        corpo_bruto=corpo, assinatura=assinatura, client_secret="secret-correto"
    )

    assert resultado is False


def test_verificar_rejeita_corpo_alterado_apos_a_assinatura() -> None:
    verifier = HmacSha256WebhookVerifier()
    secret = "client-secret-do-app-privado"
    assinatura = _assinar(b'{"id": 456}', secret)

    # Mesmo secret, corpo diferente do que foi assinado — deve falhar
    # (protege contra adulteração do payload em trânsito).
    resultado = verifier.verificar(
        corpo_bruto=b'{"id": 999}', assinatura=assinatura, client_secret=secret
    )

    assert resultado is False


def test_verificar_assinatura_com_caractere_nao_ascii_retorna_false_sem_levantar() -> None:
    # Endpoint anônimo: o header é entrada hostil. `hmac.compare_digest`
    # entre `str` levantaria TypeError (→ 500) com não-ASCII.
    verifier = HmacSha256WebhookVerifier()

    resultado = verifier.verificar(
        corpo_bruto=b'{"id": 456}', assinatura="assinatura-é-ã-ü", client_secret="segredo"
    )

    assert resultado is False


def test_verificar_rejeita_client_secret_vazio_mesmo_com_hmac_correspondente() -> None:
    # HMAC com chave vazia é calculável por qualquer um — nunca autentica.
    verifier = HmacSha256WebhookVerifier()
    corpo = b'{"id": 456}'
    assinatura = _assinar(corpo, "")

    assert verifier.verificar(corpo_bruto=corpo, assinatura=assinatura, client_secret="") is False


def test_verificar_tolera_hex_em_maiusculas_e_espacos_nas_pontas() -> None:
    verifier = HmacSha256WebhookVerifier()
    corpo = b'{"id": 456}'
    secret = "client-secret-do-app-privado"
    assinatura = f"  {_assinar(corpo, secret).upper()} "

    assert (
        verifier.verificar(corpo_bruto=corpo, assinatura=assinatura, client_secret=secret) is True
    )


def test_verificar_rejeita_assinatura_vazia() -> None:
    verifier = HmacSha256WebhookVerifier()

    assert (
        verifier.verificar(corpo_bruto=b'{"id": 456}', assinatura="", client_secret="segredo")
        is False
    )


def test_verificar_rejeita_assinatura_malformada() -> None:
    verifier = HmacSha256WebhookVerifier()

    resultado = verifier.verificar(
        corpo_bruto=b'{"id": 456}', assinatura="nao-e-um-hex-digest-valido", client_secret="segredo"
    )

    assert resultado is False
