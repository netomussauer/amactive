"""Command — usado pelo controller do webhook (resposta <3s), ver
docs/design-integracao-nuvemshop.md §5.1.

Thin command: nenhuma lógica de negócio acontece aqui, só o registro
idempotente do evento. `evento_externo_id` (`f"{canal.value}:{tipo_evento}:
{id_recurso_externo}"`, ver `domain/entities.py`) é construído dentro da
implementação concreta de `WebhookEventoRepository.registrar_se_novo`
(`infrastructure/persistence/repositories.py`) — não aqui — porque é lá que
o `INSERT ... ON CONFLICT (evento_externo_id) DO NOTHING` de fato acontece;
o Protocol (`domain/repositories.py`, fonte da verdade) recebe os três
componentes separados, não a string já montada.
"""

from __future__ import annotations

from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao, WebhookEvento
from amactive.contexts.integracao_canais.domain.repositories import WebhookEventoRepository


class RegistrarWebhookCommand:
    """Registra um `WebhookEvento` de forma idempotente e retorna
    imediatamente — o controller responde `200` independentemente de o
    evento ser novo ou duplicado (design §5.1); processamento de negócio
    (`ProcessarWebhookPedidoUseCase`) é sempre assíncrono, executado pelo
    worker."""

    def __init__(self, webhook_evento_repository: WebhookEventoRepository) -> None:
        self._webhook_eventos = webhook_evento_repository

    async def executar(
        self,
        *,
        canal: CanalIntegracao,
        tipo_evento: str,
        id_recurso_externo: str,
        payload_bruto: dict,
    ) -> WebhookEvento | None:
        """Retorna o `WebhookEvento` recém-criado, ou `None` se o evento já
        havia sido registrado anteriormente (entrega duplicada — a
        Nuvemshop declara explicitamente que isso pode ocorrer, avaliação
        §1.4). Nos dois casos, do ponto de vista do controller, a resposta
        HTTP é a mesma (`200`)."""
        return await self._webhook_eventos.registrar_se_novo(
            canal=canal,
            tipo_evento=tipo_evento,
            id_recurso_externo=id_recurso_externo,
            payload_bruto=payload_bruto,
        )
