"""Command — job de segurança, ver docs/design-integracao-nuvemshop.md §5.5.

Stretch goal de baixa prioridade dentro da Fase 1 (design §5.5/§9, passo
12), implementado depois que webhook + outbox já estavam estáveis. Mitiga o
risco "AMACTIVE fica fora do ar por mais de 48h e perde webhooks que a
Nuvemshop tentou entregar nesse intervalo" (avaliação §5): não é um caminho
de código novo, é apenas uma segunda forma de DESCOBRIR `pedido_externo_id`
candidatos — via `NuvemshopClientPort.listar_pedidos_recentes` (`GET
/orders?since=...`, paginado) em vez de via webhook.

Para cada pedido descoberto que ainda não tem NENHUM `WebhookEvento`
(independentemente de `tipo_evento`/`status` — ver
`WebhookEventoRepository.existe_evento_para_recurso`), registra um evento
sintético (`tipo_evento="reconciliacao"`) e processa via
`ProcessarWebhookPedidoUseCase`, reaproveitado integralmente, sem nenhuma
lógica de negócio duplicada — a mesma proteção de idempotência
(`pedido.UNIQUE(origem_canal, pedido_externo_id)`) que já protege o caminho
normal de webhook também protege este.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Final

import structlog

from amactive.contexts.integracao_canais.application.use_cases.processar_webhook_pedido import (
    ProcessarWebhookPedidoUseCase,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao
from amactive.contexts.integracao_canais.domain.repositories import (
    NuvemshopClientPort,
    WebhookEventoRepository,
)

# Tipo de evento sintético (nunca vem de um webhook real da Nuvemshop) usado
# para registrar candidatos descobertos por este job (design §5.5: "é apenas
# uma segunda forma de descobrir pedido_externo_id candidatos"). Precisa ser
# diferente de "order/paid" para nunca colidir, por acidente, com o
# `evento_externo_id` de um webhook genuíno sobre o mesmo recurso — ainda que
# a proteção real contra duplicidade seja `existe_evento_para_recurso`
# (abaixo), não a UNIQUE de `evento_externo_id` isoladamente.
TIPO_EVENTO_RECONCILIACAO: Final = "reconciliacao"

# Janela de retrospecção da listagem `GET /orders?since=...` quando o
# chamador não informa `desde` explicitamente. O risco mitigado (avaliação
# §5) é "AMACTIVE fora do ar por mais de 48h" — 72h dá uma margem de
# segurança acima disso, cobrindo também eventuais atrasos na própria
# cadência de execução do job (ver `scripts/run_worker.py`, ~1h) sem exigir
# agendamento perfeitamente pontual. Não é um parâmetro de configuração
# elaborado (o design §5.5 não exige isso) — só uma constante documentada,
# ajustável aqui se a experiência operacional pedir uma janela diferente.
JANELA_RETROSPECCAO: Final = timedelta(hours=72)

_logger = structlog.get_logger(__name__)


async def _confirmar_noop() -> None:
    """Callback padrão de `executar` quando o chamador não precisa de um
    commit por pedido (ex.: um teste que só inspeciona o estado final)."""
    return


class ReconciliarPedidosUseCase:
    """Ver docstring do módulo."""

    def __init__(
        self,
        *,
        nuvemshop_client: NuvemshopClientPort,
        webhook_evento_repository: WebhookEventoRepository,
        processar_webhook_pedido: ProcessarWebhookPedidoUseCase,
    ) -> None:
        self._nuvemshop = nuvemshop_client
        self._webhook_eventos = webhook_evento_repository
        self._processar_webhook_pedido = processar_webhook_pedido

    async def executar(
        self,
        *,
        desde: datetime | None = None,
        confirmar_apos_cada_pedido: Callable[[], Awaitable[None]] = _confirmar_noop,
    ) -> int:
        """Descobre pedidos recentes via `NuvemshopClientPort.
        listar_pedidos_recentes` e processa, via `ProcessarWebhookPedidoUseCase`
        (reaproveitado sem alteração — design §5.5), somente aqueles que
        ainda não têm nenhum `WebhookEvento` registrado (nem pelo webhook
        normal, nem por uma execução anterior deste próprio job). Retorna a
        quantidade de pedidos "perdidos" descobertos e processados nesta
        execução.

        `confirmar_apos_cada_pedido` (ex.: `session.commit()`) é chamado
        depois de CADA pedido ser registrado e processado, antes de tentar o
        próximo — necessário porque `VendasIntegracaoGateway.
        confirmar_pedido_externo` (design §3.1) faz um `session.rollback()`
        completo (não um SAVEPOINT) ao traduzir um `IntegrityError` em
        `PedidoExternoJaProcessado` (defesa em profundidade contra
        duplicidade, design §3.1). Sem confirmar cada pedido individualmente
        antes do próximo, esse rollback desfaria também o `webhook_evento`
        de pedidos anteriores já processados com sucesso NESTA MESMA
        execução, ainda não persistidos. O parâmetro é opcional (default
        no-op) para este caso de uso continuar sem conhecer SQLAlchemy —
        `run_worker.py` é quem passa `session.commit()`."""
        desde_efetivo = desde or (datetime.now(UTC) - JANELA_RETROSPECCAO)
        pedidos_externo_ids = await self._nuvemshop.listar_pedidos_recentes(desde=desde_efetivo)

        descobertos = 0
        for pedido_externo_id in pedidos_externo_ids:
            ja_conhecido = await self._webhook_eventos.existe_evento_para_recurso(
                canal=CanalIntegracao.NUVEMSHOP, id_recurso_externo=pedido_externo_id
            )
            if ja_conhecido:
                # Já chegou via webhook normal (qualquer status) ou já foi
                # descoberto por uma execução anterior deste job — nunca
                # recria/reprocessa (design §5.5/passo 12).
                continue

            evento = await self._webhook_eventos.registrar_se_novo(
                canal=CanalIntegracao.NUVEMSHOP,
                tipo_evento=TIPO_EVENTO_RECONCILIACAO,
                id_recurso_externo=pedido_externo_id,
                payload_bruto={"id": pedido_externo_id, "descoberto_por": "reconciliacao"},
            )
            if evento is None:
                # Corrida rara entre a checagem acima e este INSERT (ex.: o
                # webhook normal chegou nesse meio-tempo) — `ON CONFLICT DO
                # NOTHING` já cobre isso (mesma proteção de idempotência de
                # design §5.1/§5.2), nada a fazer.
                continue

            _logger.info(
                "reconciliacao.pedido_descoberto",
                pedido_externo_id=pedido_externo_id,
                evento_externo_id=evento.evento_externo_id,
            )
            await self._processar_webhook_pedido.executar(evento)
            await confirmar_apos_cada_pedido()
            descobertos += 1

        return descobertos
