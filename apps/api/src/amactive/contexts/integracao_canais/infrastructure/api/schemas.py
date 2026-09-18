"""Schemas Pydantic do endpoint de webhook — ver
docs/design-integracao-nuvemshop.md §5.1.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class WebhookRecebidoRequest(BaseModel):
    """Payload mínimo interpretado do corpo do webhook (design §5.1 passo
    4) — apenas os três campos usados para registrar o evento
    (`store_id`/`event`/`id`). O corpo bruto inteiro (não só estes três
    campos) é gravado em `webhook_evento.payload_bruto` para auditoria
    (design §2.4) — este schema só valida o mínimo necessário para montar
    `evento_externo_id`, nunca é usado para extrair itens/valores do pedido
    (isso vem de `GET /orders/{id}`, design §5.3 passo 1).

    `coerce_numbers_to_str`: a Nuvemshop envia `store_id` como NÚMERO no JSON
    (`{"store_id": 123456, ...}`), mas `credencial_canal.store_id` é texto —
    sem a coerção o Pydantic v2 rejeita int para `str`. `max_length` de
    `event` acompanha `webhook_evento.tipo_evento varchar(50)` (migration
    000005): um valor maior estouraria no INSERT."""

    model_config = ConfigDict(coerce_numbers_to_str=True)

    store_id: str = Field(max_length=100)
    event: str = Field(max_length=50)
    id: int


class WebhookRecebidoResponse(BaseModel):
    """Resposta `200` sempre, independentemente de o evento ser novo ou
    duplicado (design §5.1 passo 6) — nenhum processamento de negócio
    acontece na requisição."""

    recebido: bool = True
