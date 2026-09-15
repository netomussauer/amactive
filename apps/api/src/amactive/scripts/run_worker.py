"""Worker de longa duração (loop) que processa as filas assíncronas do
contexto `integracao_canais` — ver docs/design-integracao-nuvemshop.md
§4.5/§9 (passos 7 e 8).

IMPORTANTE — diferente dos demais scripts deste pacote
(`apply_migrations.py`, `bootstrap_admin.py`, `bootstrap_usuario_integracao.py`,
`configurar_credencial_nuvemshop.py`), que executam uma tarefa única e
terminam: este módulo é um **processo de longa duração**. Um loop
assíncrono com tick curto (`_TICK_SEGUNDOS`, 2s) roda indefinidamente até
receber `SIGTERM` (rollout do Kubernetes — ver design §4.5, "compatível com
rollout do Kubernetes") ou `SIGINT` (Ctrl+C local), quando desliga
graciosamente: nunca interrompe um tick em andamento, só para de iniciar
o próximo.

Nesta versão (design §9 passos 7, 8 e 12), o worker processa, no mesmo tick,
as filas de `integracao_estoque_outbox` (`PublicarEstoqueCanalUseCase`) e
`integracao_catalogo_outbox` (`PublicarCatalogoCanalUseCase`) — a fila de
`webhook_evento` alimentada pelo endpoint de webhook (`POST
/integracoes/nuvemshop/webhooks`) ainda não é consumida por este loop
(gap fora do escopo do passo 12/reconciliação, que só invoca
`ProcessarWebhookPedidoUseCase` diretamente para os eventos que ELE MESMO
descobre e registra — ver `ReconciliarPedidosUseCase`). A expectativa do
design (§4.5) é que os consumos passem a coexistir no mesmo processo/loop,
não que cada fila ganhe um `Deployment` próprio.

Além disso, a cada `_INTERVALO_RECONCILIACAO` (não a cada tick de
`_TICK_SEGUNDOS` — ver justificativa junto à constante, abaixo), o worker
roda `ReconciliarPedidosUseCase` (design §5.5/§9 passo 12): descobre
pedidos "perdidos" (nunca entregues via webhook, ex.: AMACTIVE fora do ar
por mais de 48h) via listagem paginada da Nuvemshop e os processa pelo
mesmo `ProcessarWebhookPedidoUseCase` do fluxo normal.

A credencial da Nuvemshop é resolvida uma única vez no startup (design
§7.2: "leitura ... uma vez no startup do worker") e o `NuvemshopHttpClient`
resultante é reaproveitado por todos os ticks — uma rotação de credencial
via `configurar_credencial_nuvemshop.py` exige reiniciar o worker (aceitável:
é uma operação rara e manual, ver design §7.2).

Uso (processo de longa duração — não roda via `kubectl exec` como os demais
scripts, é o `Deployment amactive-worker`, infra fora do escopo deste
módulo, ver design §9 item 9):
    python -m amactive.scripts.run_worker
"""

from __future__ import annotations

import asyncio
import signal
import sys
from datetime import UTC, datetime, timedelta
from typing import Final

from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.integracao_canais.application.use_cases.processar_webhook_pedido import (
    ProcessarWebhookPedidoUseCase,
)
from amactive.contexts.integracao_canais.application.use_cases.publicar_catalogo_canal import (
    LIMITE_LOTE_PADRAO as LIMITE_LOTE_PADRAO_CATALOGO,
)
from amactive.contexts.integracao_canais.application.use_cases.publicar_catalogo_canal import (
    PublicarCatalogoCanalUseCase,
)
from amactive.contexts.integracao_canais.application.use_cases.publicar_estoque_canal import (
    LIMITE_LOTE_PADRAO as LIMITE_LOTE_PADRAO_ESTOQUE,
)
from amactive.contexts.integracao_canais.application.use_cases.publicar_estoque_canal import (
    PublicarEstoqueCanalUseCase,
)
from amactive.contexts.integracao_canais.application.use_cases.reconciliar_pedidos import (
    ReconciliarPedidosUseCase,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao
from amactive.contexts.integracao_canais.domain.exceptions import CredencialCanalAusente
from amactive.contexts.integracao_canais.infrastructure.gateways.cadastros_gateway import (
    CadastrosIntegracaoGateway,
)
from amactive.contexts.integracao_canais.infrastructure.gateways.catalogo_gateway import (
    CatalogoIntegracaoGateway,
)
from amactive.contexts.integracao_canais.infrastructure.gateways.vendas_gateway import (
    VendasIntegracaoGateway,
)
from amactive.contexts.integracao_canais.infrastructure.metrics import integracao_outbox_pendente
from amactive.contexts.integracao_canais.infrastructure.nuvemshop.client import (
    NuvemshopHttpClient,
)
from amactive.contexts.integracao_canais.infrastructure.persistence.repositories import (
    SqlAlchemyCredencialCanalRepository,
    SqlAlchemyIntegracaoCatalogoOutboxRepository,
    SqlAlchemyIntegracaoEstoqueOutboxRepository,
    SqlAlchemyMapeamentoVarianteRepository,
    SqlAlchemyWebhookEventoRepository,
)
from amactive.shared_kernel.database import async_session_factory

# Tick curto (design §4.5) — o rate limiter do client (2 req/s, §4.4/§7.3) já
# é o limitador real de throughput; um tick curto só garante baixa latência
# entre "venda no PDV"/"edição de produto" e a publicação na Nuvemshop
# (design §9 item 7: "dentro de segundos").
_TICK_SEGUNDOS: Final = 2.0

# Cadência do job de reconciliação (design §5.5/§9 passo 12) — muito mais
# baixa que `_TICK_SEGUNDOS`: rodar a cada 2s estressaria o rate limit da
# Nuvemshop (2 req/s, compartilhado com estoque/catálogo/webhook) à toa,
# listando pedidos que, na esmagadora maioria das vezes, já chegaram pelo
# webhook normal segundos antes. O risco mitigado (avaliação §5) é "AMACTIVE
# fora do ar por mais de 48h" — não há necessidade de reagir em segundos, só
# de eventualmente descobrir o que o webhook perdeu. 1h é um meio-termo
# razoável para um MVP entre o "job diário" citado pela avaliação §3.5/§5 e
# uma reação mais ágil (qualquer valor entre 1h e 24h seria defensável; não
# configurável via env var por não haver necessidade clara disso hoje —
# ajustar aqui se a operação real pedir outra cadência).
_INTERVALO_RECONCILIACAO: Final = timedelta(hours=1)


async def _resolver_client_nuvemshop() -> NuvemshopHttpClient:
    """Lê e decifra a credencial ativa uma única vez, no startup (design
    §7.2). Sem credencial configurada, o worker não pode operar — levanta
    `CredencialCanalAusente` para que o processo termine com uma mensagem
    de erro clara, em vez de ficar rodando sem poder publicar nada."""
    async with async_session_factory() as session:
        credencial = await SqlAlchemyCredencialCanalRepository(session).buscar_token_decifrado(
            CanalIntegracao.NUVEMSHOP
        )
    if credencial is None:
        raise CredencialCanalAusente(
            "Nenhuma credencial NUVEMSHOP configurada — rode "
            "`python -m amactive.scripts.configurar_credencial_nuvemshop` antes de iniciar "
            "o worker."
        )
    return NuvemshopHttpClient(store_id=credencial.store_id, access_token=credencial.access_token)


async def _processar_estoque(session: AsyncSession, nuvemshop_client: NuvemshopHttpClient) -> int:
    outbox_repo = SqlAlchemyIntegracaoEstoqueOutboxRepository(session)
    mapeamento_repo = SqlAlchemyMapeamentoVarianteRepository(session)
    use_case = PublicarEstoqueCanalUseCase(
        nuvemshop_client=nuvemshop_client,
        mapeamento_variante_repository=mapeamento_repo,
        outbox_repository=outbox_repo,
    )
    processados = await use_case.executar(limite=LIMITE_LOTE_PADRAO_ESTOQUE)
    # Gauge `integracao_outbox_pendente{fila="estoque"}` (design §8) —
    # mesma query já necessária para o alerta operacional, nenhuma consulta
    # nova além de `contar_pendentes` (design §2.5/§8).
    integracao_outbox_pendente.labels(fila="estoque").set(await outbox_repo.contar_pendentes())
    return processados


async def _processar_catalogo(session: AsyncSession, nuvemshop_client: NuvemshopHttpClient) -> int:
    outbox_repo = SqlAlchemyIntegracaoCatalogoOutboxRepository(session)
    mapeamento_repo = SqlAlchemyMapeamentoVarianteRepository(session)
    catalogo_gateway = CatalogoIntegracaoGateway(session)
    use_case = PublicarCatalogoCanalUseCase(
        nuvemshop_client=nuvemshop_client,
        catalogo_integracao_port=catalogo_gateway,
        mapeamento_variante_repository=mapeamento_repo,
        outbox_repository=outbox_repo,
    )
    processados = await use_case.executar(limite=LIMITE_LOTE_PADRAO_CATALOGO)
    # Gauge `integracao_outbox_pendente{fila="catalogo"}` (design §8) — idem
    # `_processar_estoque`.
    integracao_outbox_pendente.labels(fila="catalogo").set(await outbox_repo.contar_pendentes())
    return processados


async def _processar_reconciliacao(
    session: AsyncSession, nuvemshop_client: NuvemshopHttpClient
) -> int:
    """Uma execução completa de `ReconciliarPedidosUseCase` (design §5.5) —
    chamada por `_processar_reconciliacao_se_devido` só quando o intervalo
    de cadência (`_INTERVALO_RECONCILIACAO`) já decorreu, nunca a cada
    tick."""
    webhook_repo = SqlAlchemyWebhookEventoRepository(session)
    processar_webhook_pedido = ProcessarWebhookPedidoUseCase(
        nuvemshop_client=nuvemshop_client,
        cliente_integracao=CadastrosIntegracaoGateway(session),
        mapeamento_variante_repository=SqlAlchemyMapeamentoVarianteRepository(session),
        pedido_integracao=VendasIntegracaoGateway(session),
        webhook_evento_repository=webhook_repo,
    )
    use_case = ReconciliarPedidosUseCase(
        nuvemshop_client=nuvemshop_client,
        webhook_evento_repository=webhook_repo,
        processar_webhook_pedido=processar_webhook_pedido,
    )
    # `confirmar_apos_cada_pedido=session.commit` — ver docstring de
    # `ReconciliarPedidosUseCase.executar` para a razão (o rollback completo
    # de `VendasIntegracaoGateway.confirmar_pedido_externo` em caso de
    # `PedidoExternoJaProcessado` desfaria pedidos anteriores desta mesma
    # execução se não fossem confirmados individualmente).
    return await use_case.executar(confirmar_apos_cada_pedido=session.commit)


async def _processar_reconciliacao_se_devido(
    nuvemshop_client: NuvemshopHttpClient, ultima_execucao_em: datetime | None
) -> datetime | None:
    """Controle de cadência do job de reconciliação (design §9 passo 12):
    compara o relógio de parede contra o timestamp da última execução,
    mantido em memória do próprio processo (não persistido — uma
    reinicialização do worker apenas antecipa a próxima execução, o que é
    aceitável para um job de segurança de baixa prioridade). Só abre uma
    sessão/transação quando o intervalo já decorreu — nunca a cada tick de
    `_TICK_SEGUNDOS`."""
    agora = datetime.now(UTC)
    if ultima_execucao_em is not None and (agora - ultima_execucao_em) < _INTERVALO_RECONCILIACAO:
        return ultima_execucao_em

    async with async_session_factory() as session:
        try:
            descobertos = await _processar_reconciliacao(session, nuvemshop_client)
        except Exception:
            await session.rollback()
            raise
    if descobertos:
        print(f"[worker] reconciliação: {descobertos} pedido(s) perdido(s) descoberto(s).")
    return agora


async def _processar_um_tick(nuvemshop_client: NuvemshopHttpClient) -> None:
    """Uma sessão/transação por tick — nunca reaproveitada entre ticks
    (mesmo princípio de `get_db_session`: uma sessão por unidade de
    trabalho). Processa as duas filas (estoque e catálogo, design §9 passos
    7/8) na mesma sessão/transação — falha em qualquer uma das duas faz
    rollback do tick inteiro e propaga; quem chama decide se o worker
    continua vivo (ver `_executar_loop`)."""
    async with async_session_factory() as session:
        try:
            processados_estoque = await _processar_estoque(session, nuvemshop_client)
            processados_catalogo = await _processar_catalogo(session, nuvemshop_client)
        except Exception:
            await session.rollback()
            raise
        await session.commit()
        if processados_estoque:
            print(f"[worker] outbox de estoque: {processados_estoque} variante(s) processada(s).")
        if processados_catalogo:
            print(f"[worker] outbox de catálogo: {processados_catalogo} produto(s) processado(s).")


async def _executar_loop(parar: asyncio.Event) -> None:
    nuvemshop_client = await _resolver_client_nuvemshop()
    print(
        "[worker] iniciado — consumindo integracao_estoque_outbox e "
        f"integracao_catalogo_outbox a cada {_TICK_SEGUNDOS}s (design §4.5/§9 passos 7/8); "
        f"reconciliação de pedidos (§5.5/§9 passo 12) a cada {_INTERVALO_RECONCILIACAO}."
    )
    # Timestamp da última execução do job de reconciliação, em memória do
    # processo (design §9 passo 12) — `None` até a primeira execução, que
    # acontece assim que o worker sobe (não espera um `_INTERVALO_RECONCILIACAO`
    # inicial): um worker recém-iniciado é justamente o momento em que faz
    # mais sentido checar por pedidos perdidos enquanto esteve fora do ar.
    ultima_reconciliacao_em: datetime | None = None
    try:
        while not parar.is_set():
            try:
                await _processar_um_tick(nuvemshop_client)
            except Exception as exc:  # noqa: BLE001 — 1 tick com falha nunca derruba o worker
                print(f"[worker] falha no tick (será tentado novamente): {exc}", file=sys.stderr)

            try:
                ultima_reconciliacao_em = await _processar_reconciliacao_se_devido(
                    nuvemshop_client, ultima_reconciliacao_em
                )
            except Exception as exc:  # noqa: BLE001 — idem: nunca derruba o worker
                print(
                    f"[worker] falha na reconciliação (será tentada novamente no próximo "
                    f"intervalo de {_INTERVALO_RECONCILIACAO}): {exc}",
                    file=sys.stderr,
                )
                # Mesmo em falha, marca "tentado agora" — evita martelar a
                # Nuvemshop a cada tick de 2s enquanto o erro persistir
                # (ex.: credencial revogada); a próxima tentativa só ocorre
                # depois de um `_INTERVALO_RECONCILIACAO` completo.
                ultima_reconciliacao_em = datetime.now(UTC)

            try:
                # Espera até o próximo tick, mas acorda imediatamente se
                # `parar` for sinalizado no meio da espera — desligamento
                # ágil sem nunca interromper um tick já em andamento.
                await asyncio.wait_for(parar.wait(), timeout=_TICK_SEGUNDOS)
            except TimeoutError:
                pass
    finally:
        print("[worker] desligando graciosamente...")


def _instalar_handlers_de_desligamento(parar: asyncio.Event) -> None:
    """`SIGTERM` — compatível com rollout do Kubernetes (design §4.5).
    `SIGINT` também tratado, para permitir Ctrl+C em desenvolvimento local.

    `loop.add_signal_handler` não é suportado pelo event loop padrão do
    Windows (`NotImplementedError`) — fallback para `signal.signal` síncrono
    nesse caso (só relevante para rodar este script fora de Docker/WSL em
    desenvolvimento; em produção o worker sempre roda em um container
    Linux)."""
    loop = asyncio.get_running_loop()
    for sinal in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sinal, parar.set)
        except NotImplementedError:
            signal.signal(sinal, lambda *_args: parar.set())


async def _main_async() -> None:
    parar = asyncio.Event()
    _instalar_handlers_de_desligamento(parar)
    await _executar_loop(parar)


def main() -> None:
    try:
        asyncio.run(_main_async())
    except CredencialCanalAusente as exc:
        print(f"Falha ao iniciar o worker: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:
        print(f"Falha inesperada no worker: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
