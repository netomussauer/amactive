"""Testes unitários das métricas Prometheus específicas do contexto
Integração de Canais (`infrastructure/metrics.py`) — ver
docs/design-integracao-nuvemshop.md §8/§9 passo 11.

Não há nenhum padrão de teste de métrica já estabelecido no projeto (grep em
`tests/` não encontra `prometheus_client`/`REGISTRY` antes deste arquivo) —
por isso o teste mais simples e direto possível: usa o
`prometheus_client.REGISTRY` (mesmo registry default usado por
`prometheus-fastapi-instrumentator` em `main.py`) para confirmar que cada
métrica está registrada com o nome/rótulos corretos e que o valor
incrementa/atualiza exatamente como o código de produção a invoca
(`infrastructure/api/router.py`, `infrastructure/persistence/repositories.py`,
`infrastructure/nuvemshop/client.py`, `scripts/run_worker.py`)."""

from __future__ import annotations

import pytest
from prometheus_client import REGISTRY

from amactive.contexts.integracao_canais.infrastructure import metrics

pytestmark = pytest.mark.unit


def _valor(nome: str, labels: dict[str, str] | None = None) -> float:
    valor = REGISTRY.get_sample_value(nome, labels)
    return valor if valor is not None else 0.0


def test_webhook_evento_recebido_total_incrementa_por_tipo_evento() -> None:
    labels = {"tipo_evento": "order/paid-teste-metrica"}
    antes = _valor("webhook_evento_recebido_total", labels)

    # Mesma chamada feita por `infrastructure/api/router.py` ao receber um
    # webhook autenticado (design §8).
    metrics.webhook_evento_recebido_total.labels(tipo_evento="order/paid-teste-metrica").inc()

    assert _valor("webhook_evento_recebido_total", labels) == antes + 1


def test_webhook_evento_conflito_manual_total_incrementa() -> None:
    antes = _valor("webhook_evento_conflito_manual_total")

    # Mesma chamada feita por
    # `SqlAlchemyWebhookEventoRepository.marcar_conflito_manual` (design
    # §5.4/§8).
    metrics.webhook_evento_conflito_manual_total.inc()

    assert _valor("webhook_evento_conflito_manual_total") == antes + 1


def test_integracao_outbox_pendente_atualiza_por_fila() -> None:
    # Mesma chamada feita por `scripts/run_worker.py` a cada tick, uma vez
    # por fila (design §8) — é um gauge (`.set(...)`), não um contador.
    metrics.integracao_outbox_pendente.labels(fila="estoque").set(3)
    metrics.integracao_outbox_pendente.labels(fila="catalogo").set(7)
    metrics.integracao_outbox_pendente.labels(fila="webhook").set(5)

    assert _valor("integracao_outbox_pendente", {"fila": "estoque"}) == 3
    assert _valor("integracao_outbox_pendente", {"fila": "catalogo"}) == 7
    assert _valor("integracao_outbox_pendente", {"fila": "webhook"}) == 5

    metrics.integracao_outbox_pendente.labels(fila="estoque").set(0)
    assert _valor("integracao_outbox_pendente", {"fila": "estoque"}) == 0


def test_nuvemshop_client_requisicoes_total_incrementa_por_status_code() -> None:
    labels_200 = {"status_code": "200"}
    labels_erro_rede = {"status_code": "erro_rede"}
    antes_200 = _valor("nuvemshop_client_requisicoes_total", labels_200)
    antes_erro_rede = _valor("nuvemshop_client_requisicoes_total", labels_erro_rede)

    # Mesma chamada feita por `infrastructure/nuvemshop/client.py`,
    # `NuvemshopHttpClient._request` (design §8) — um rótulo por
    # `status_code` HTTP, e o rótulo sentinela `erro_rede` para falhas sem
    # resposta HTTP.
    metrics.nuvemshop_client_requisicoes_total.labels(status_code="200").inc()
    metrics.nuvemshop_client_requisicoes_total.labels(status_code="erro_rede").inc()

    assert _valor("nuvemshop_client_requisicoes_total", labels_200) == antes_200 + 1
    assert _valor("nuvemshop_client_requisicoes_total", labels_erro_rede) == antes_erro_rede + 1
