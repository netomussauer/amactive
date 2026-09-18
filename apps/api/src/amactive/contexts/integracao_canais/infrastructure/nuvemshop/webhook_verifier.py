"""Verificação HMAC-SHA256 de webhooks da Nuvemshop — ver
docs/design-integracao-nuvemshop.md §5.1.

Função pura, sem I/O — implementa `WebhookVerifierPort`
(`domain/repositories.py`). Fácil de testar isoladamente (ver
tests/unit/test_nuvemshop_webhook_verifier.py).
"""

from __future__ import annotations

import hashlib
import hmac


class HmacSha256WebhookVerifier:
    """Compara a assinatura recebida no header `x-linkedstore-hmac-sha256`
    (avaliação §1.4) contra o HMAC-SHA256 do corpo bruto do webhook,
    calculado com o `client_secret` do app privado — sempre via
    `hmac.compare_digest` (resistente a timing attack), nunca `==`.

    Endpoint anônimo: o header é entrada hostil. A comparação é feita em
    `bytes` porque `compare_digest` entre `str` levanta `TypeError` (→ 500)
    se qualquer lado tiver caractere não-ASCII, e o Starlette decodifica
    headers como latin-1. Um `client_secret` vazio é rejeitado: o HMAC com
    chave vazia é calculável por qualquer um."""

    def verificar(self, *, corpo_bruto: bytes, assinatura: str, client_secret: str) -> bool:
        if not client_secret:
            return False
        esperado = hmac.new(client_secret.encode("utf-8"), corpo_bruto, hashlib.sha256).hexdigest()
        recebido = assinatura.strip().lower()
        return hmac.compare_digest(esperado.encode("ascii"), recebido.encode("utf-8", "replace"))
