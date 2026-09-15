"""Command — job de segurança, ver docs/design-integracao-nuvemshop.md §5.5.

Ainda não implementado — stub reservado por design §2.2. Stretch goal de
baixa prioridade dentro da Fase 1 (design §5.5/§9, passo 12): implementável
só depois que webhook + outbox estiverem estáveis, sem bloquear o restante
do plano. Reaproveita integralmente `ProcessarWebhookPedidoUseCase` e a
mesma proteção de idempotência (`pedido.UNIQUE(origem_canal,
pedido_externo_id)`) — descobre `pedido_externo_id` candidatos via
`GET /orders?since=...` em vez de via webhook.
"""

from __future__ import annotations
