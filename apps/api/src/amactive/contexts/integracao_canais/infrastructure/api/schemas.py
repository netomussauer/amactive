"""Schemas Pydantic do endpoint de webhook — ver
docs/design-integracao-nuvemshop.md §5.1.
"""

from __future__ import annotations

from pydantic import BaseModel


class WebhookRecebidoRequest(BaseModel):
    """Payload mínimo interpretado do corpo do webhook (design §5.1 passo
    4) — apenas os três campos usados para registrar o evento
    (`store_id`/`event`/`id`). O corpo bruto inteiro (não só estes três
    campos) é gravado em `webhook_evento.payload_bruto` para auditoria
    (design §2.4) — este schema só valida o mínimo necessário para montar
    `evento_externo_id`, nunca é usado para extrair itens/valores do pedido
    (isso vem de `GET /orders/{id}`, design §5.3 passo 1)."""

    store_id: str
    event: str
    id: int


class WebhookRecebidoResponse(BaseModel):
    """Resposta `200` sempre, independentemente de o evento ser novo ou
    duplicado (design §5.1 passo 6) — nenhum processamento de negócio
    acontece na requisição."""

    recebido: bool = True
