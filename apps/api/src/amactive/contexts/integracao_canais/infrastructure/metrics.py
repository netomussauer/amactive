"""Métricas Prometheus específicas do contexto Integração de Canais — ver
docs/design-integracao-nuvemshop.md §8.

Estende as métricas RED automáticas já expostas por
`prometheus-fastapi-instrumentator` (`main.py`, ver docs/SDD.md §5.3) com
sinais de negócio específicos desta integração — nenhuma delas substitui ou
reconfigura o `Instrumentator` já registrado, apenas usa o mesmo registry
default do `prometheus_client` (a mesma instância que o Instrumentator usa
por baixo, exposta pelo mesmo endpoint `/metrics`).

Os objetos de métrica são definidos uma única vez, aqui, e importados por
quem precisa incrementá-los/atualizá-los (`infrastructure/api/router.py`,
`infrastructure/persistence/repositories.py`,
`infrastructure/nuvemshop/client.py`, `scripts/run_worker.py`) — evita
`ValueError: Duplicated timeseries in CollectorRegistry` por registrar o
mesmo nome de métrica mais de uma vez."""

from __future__ import annotations

from prometheus_client import Counter, Gauge

# Controller do webhook (design §5.1/§8) — incrementada para todo webhook
# recebido e autenticado (assinatura HMAC válida), antes de qualquer decisão
# de idempotência (evento novo ou duplicado contam igualmente aqui; a
# duplicidade já é observável separadamente via `webhook_evento.tentativas`/
# logs, não é objetivo desta métrica).
webhook_evento_recebido_total = Counter(
    "webhook_evento_recebido_total",
    "Quantidade de webhooks da Nuvemshop recebidos e autenticados, por tipo de evento.",
    labelnames=["tipo_evento"],
)

# `WebhookEventoRepository.marcar_conflito_manual` (design §5.4/§8) — é o
# sinal de alerta operacional da fila de conflito manual (não há tabela
# dedicada nesta fase, ver design §5.4: "observabilidade expõe uma métrica
# ... e um log estruturado nível ERROR").
webhook_evento_conflito_manual_total = Counter(
    "webhook_evento_conflito_manual_total",
    "Quantidade de webhook_evento marcados como CONFLITO_MANUAL.",
)

# Consulta periódica do worker (`scripts/run_worker.py`, design §8) — o
# tamanho da fila é o principal indicador de saúde da sincronização.
# `fila` é sempre "estoque", "catalogo" ou "webhook" (design §8, mesmos
# rótulos citados na tabela de observabilidade; "webhook" = `webhook_evento`
# em `PENDENTE`/`ERRO`, ainda não consumido pelo worker).
integracao_outbox_pendente = Gauge(
    "integracao_outbox_pendente",
    "Quantidade de linhas PENDENTE/ERRO em cada fila de outbox de integração.",
    labelnames=["fila"],
)

# `infrastructure/nuvemshop/client.py`, método `_request` — todo request
# passa por ali (design §8). `status_code` é sempre uma string (o rótulo de
# uma métrica Prometheus é sempre texto) — para falhas de rede sem resposta
# HTTP (timeout, conexão recusada), usa-se o valor sentinela
# `"erro_rede"` (nenhum `status_code` HTTP existe nesse caso).
nuvemshop_client_requisicoes_total = Counter(
    "nuvemshop_client_requisicoes_total",
    "Quantidade de requisições HTTP feitas à API da Nuvemshop, por status_code de resposta.",
    labelnames=["status_code"],
)
