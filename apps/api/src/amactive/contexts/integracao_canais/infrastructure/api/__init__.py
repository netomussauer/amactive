"""Adapter HTTP (FastAPI) do contexto Integração de Canais.

Implementado no passo 6 da sequência de docs/design-integracao-nuvemshop.md
§9:

- ``router.py`` — ``POST /integracoes/nuvemshop/webhooks`` (público, sem
  JWT, verificado por HMAC — ver §5.1).
- ``schemas.py`` — Pydantic, payload mínimo do webhook
  (``WebhookRecebidoRequest``).
"""

from __future__ import annotations
