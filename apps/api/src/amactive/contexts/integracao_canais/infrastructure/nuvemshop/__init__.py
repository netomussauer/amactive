"""ACL de infraestrutura para a API da Nuvemshop.

Pasta reservada por docs/design-integracao-nuvemshop.md §2.2 — ainda vazia
neste esqueleto (passo 2 da sequência de implementação, §9). Conteúdo
futuro, a ser implementado no passo 5:

- ``client.py`` — ``NuvemshopClientPort`` (HTTP client + rate limiter +
  retry, ver §7).
- ``mappers.py`` — tradução payload Nuvemshop <-> DTOs internos
  (``domain/repositories.py``).
- ``webhook_verifier.py`` — ``WebhookVerifierPort`` (HMAC-SHA256, ver §5.1).
"""

from __future__ import annotations
