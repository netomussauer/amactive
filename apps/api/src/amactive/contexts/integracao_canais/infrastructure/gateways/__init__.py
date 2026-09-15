"""Gateways que implementam as portas cross-context de ``domain/repositories.py``.

Implementados no passo 6 da sequência de docs/design-integracao-nuvemshop.md
§9:

- ``vendas_gateway.py`` — implementa ``PedidoIntegracaoPort`` chamando
  ``CriarPedidoUseCase`` in-process (§3.1/§3.4).
- ``cadastros_gateway.py`` — implementa ``ClienteIntegracaoPort`` chamando
  ``ClienteRepository.upsert_por_email`` (§3.3).
- ``catalogo_gateway.py`` — implementa ``CatalogoIntegracaoPort``, somente
  leitura (§3.2).
"""

from __future__ import annotations
