"""Command — consumo da fila `webhook_evento`, ver
docs/design-integracao-nuvemshop.md §4.5/§5.3/§9 (passo 7).

O endpoint público `POST /integracoes/nuvemshop/webhooks` só REGISTRA o
evento (`PENDENTE`) e responde 200; este caso de uso é o que, chamado a cada
tick do worker (`scripts/run_worker.py`), transforma esse evento em pedido —
via `ProcessarWebhookPedidoUseCase`, reaproveitado sem alteração. Sem ele,
webhooks seriam recebidos e jamais virariam pedidos.

Regras de consumo (todas decididas, não configuráveis):

- Só `tipo_evento` em `TIPOS_EVENTO_PROCESSAVEIS` (`order/paid`, o único tipo
  assinado na Fase 1, e `reconciliacao`, o sintético de
  `ReconciliarPedidosUseCase`) chegam a `ProcessarWebhookPedidoUseCase`.
  QUALQUER outro tipo (ex.: um futuro `order/cancelled` que alguém assine na
  Nuvemshop) nunca cria pedido: é logado (`webhook_evento.ignorado`, sem o
  payload) e marcado `PROCESSADO` — o enum `status_webhook_evento` não tem
  um status `IGNORADO` e não se cria migration só para isso.
- Teto de tentativas (`MAX_TENTATIVAS_WEBHOOK`): um evento `ERRO` com
  `tentativas >= MAX_TENTATIVAS_WEBHOOK` NÃO é reprocessado — vai para
  `CONFLITO_MANUAL` (log ERROR + métrica `webhook_evento_conflito_manual_total`,
  via `marcar_conflito_manual`). Encerra o loop infinito de um evento
  envenenado e o expõe na fila de conflito manual (design §5.4).
- Backoff EM MEMÓRIA (`BackoffWebhookEmMemoria`): `webhook_evento` não tem
  `proxima_tentativa_em` (diferente dos outbox, design §4.3) e `marcar_erro`
  não grava timestamp; sem isto, um erro transitório (Nuvemshop fora do ar)
  seria reprocessado a cada tick de 2s e queimaria o teto em segundos. O
  estado vive no processo do worker (ver `run_worker.py`): reiniciar o
  worker o zera, o que só ANTECIPA retentativas de eventos `ERRO` — nunca as
  perde nem duplica pedidos (idempotência por `pedido.UNIQUE`,
  design §5.2) —, por isso é aceitável não persisti-lo.
- Um erro inesperado (exceção não tratada por `ProcessarWebhookPedidoUseCase`)
  em UM evento nunca impede os demais do lote nem derruba o tick: é
  capturado, a transação é revertida (`reverter_apos_erro`) e o evento é
  marcado `ERRO` (`tentativas += 1`), seguindo o mesmo caminho de backoff/teto
  de qualquer outro erro transitório.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Final
from uuid import UUID

import structlog

from amactive.contexts.integracao_canais.application.use_cases._backoff_outbox import (
    calcular_backoff_segundos,
)
from amactive.contexts.integracao_canais.application.use_cases.processar_webhook_pedido import (
    TIPO_EVENTO_PEDIDO_PAGO,
    ProcessarWebhookPedidoUseCase,
)
from amactive.contexts.integracao_canais.application.use_cases.reconciliar_pedidos import (
    TIPO_EVENTO_RECONCILIACAO,
)
from amactive.contexts.integracao_canais.domain.entities import WebhookEvento
from amactive.contexts.integracao_canais.domain.repositories import WebhookEventoRepository

# Lote pequeno por tick — `order/paid` é o fluxo mais sensível a latência
# (design §4.5), mas cada evento custa pelo menos 1 chamada `GET /orders/{id}`
# ao rate limiter compartilhado da Nuvemshop (2 req/s, §4.4/§7.3); 10 eventos
# por tick de 2s já cobre o volume esperado (avaliação §7) sem monopolizá-lo.
LIMITE_LOTE_PADRAO: Final = 10

# Teto de tentativas de um evento `ERRO` (design §4.3/§5.3, mesmo espírito de
# `MAX_TENTATIVAS_OUTBOX`, mas maior: aqui não há coluna de `proxima_tentativa_em`
# nem "falha definitiva" 4xx separada, e um pedido pago perdido custa mais que
# uma publicação de estoque atrasada). Com backoff exponencial limitado a
# `BACKOFF_MAXIMO_SEGUNDOS`, 12 tentativas cobrem ~23 min de indisponibilidade
# (2+4+...+256s + 3x300s, sem contar o jitter) antes de escalar para conflito
# manual.
MAX_TENTATIVAS_WEBHOOK: Final = 12

# Teto de UMA espera de backoff — sem ele, `2**tentativas` chegaria a ~68 min
# na 12ª tentativa, tempo demais para um pedido já pago na Nuvemshop.
BACKOFF_MAXIMO_SEGUNDOS: Final = 300.0

# Único conjunto de tipos que pode virar pedido — ver docstring do módulo.
TIPOS_EVENTO_PROCESSAVEIS: Final = frozenset({TIPO_EVENTO_PEDIDO_PAGO, TIPO_EVENTO_RECONCILIACAO})

# `erro_detalhe` é `Text`, mas o texto de uma exceção inesperada (ex.: um
# `DBAPIError` com SQL e parâmetros) pode ser enorme — limita o que é gravado.
_DETALHE_MAX_CARACTERES: Final = 500

# Log estruturado a cada transição de status (design §8) — sempre com
# `evento_externo_id`, nunca o payload bruto (pode conter dados pessoais do
# comprador) nem qualquer token/secret.
_logger = structlog.get_logger(__name__)


async def _noop() -> None:
    """Callback padrão de `confirmar_apos_cada_evento`/`reverter_apos_erro`
    quando o chamador não precisa de controle transacional (ex.: um teste
    que só inspeciona o estado final)."""
    return


class BackoffWebhookEmMemoria:
    """Estado de backoff por evento (`evento_id` -> instante da próxima
    tentativa permitida), mantido em memória do processo do worker.

    Existe como objeto separado do caso de uso porque o `run_worker.py`
    recria o caso de uso (e seus repositórios/gateways, presos à sessão do
    tick) a CADA tick, mas este estado precisa sobreviver entre ticks: uma
    única instância é criada no startup do worker e injetada em cada caso de
    uso novo. Nunca segura uma `AsyncSession`.

    Política: espera de `2**tentativas` segundos com jitter de ±20% e teto de
    `BACKOFF_MAXIMO_SEGUNDOS`. Reutiliza `calcular_backoff_segundos` dos
    outbox (mesmo pacote, mesma fórmula exata: tentativa 1 -> 2s, 2 -> 4s,
    ...) e só acrescenta o teto por cima. O relógio é monotônico (imune a
    ajuste de relógio de parede) e injetável para testes determinísticos.
    """

    def __init__(self, *, relogio: Callable[[], float] = time.monotonic) -> None:
        self._relogio = relogio
        self._proxima_tentativa: dict[UUID, float] = {}

    def __len__(self) -> int:
        return len(self._proxima_tentativa)

    def em_janela(self, evento_id: UUID) -> bool:
        """`True` se o evento ainda está aguardando o backoff da última
        tentativa (deve ser pulado neste tick)."""
        proxima = self._proxima_tentativa.get(evento_id)
        return proxima is not None and self._relogio() < proxima

    def registrar_tentativa(self, evento_id: UUID, *, tentativas_apos_falha: int) -> float:
        """Agenda a próxima tentativa permitida e devolve a espera escolhida
        (segundos). `tentativas_apos_falha` é o valor que `tentativas` terá
        no banco se a tentativa que acabou de ocorrer terminou em
        `marcar_erro` (`tentativas` do evento lido + 1)."""
        espera = min(
            calcular_backoff_segundos(max(1, tentativas_apos_falha)), BACKOFF_MAXIMO_SEGUNDOS
        )
        self._proxima_tentativa[evento_id] = self._relogio() + espera
        return espera

    def podar_expirados(self) -> None:
        """Descarta janelas já vencidas — mantém o dicionário limitado (uma
        entrada também é registrada para tentativas que terminaram em
        `PROCESSADO`/`CONFLITO_MANUAL`, porque `ProcessarWebhookPedidoUseCase`
        não informa o desfecho; essas entradas nunca são consultadas de novo
        e somem aqui assim que expiram)."""
        agora = self._relogio()
        vencidos = [eid for eid, proxima in self._proxima_tentativa.items() if proxima <= agora]
        for eid in vencidos:
            del self._proxima_tentativa[eid]


class ConsumirWebhooksPendentesUseCase:
    """Ver docstring do módulo."""

    def __init__(
        self,
        *,
        webhook_evento_repository: WebhookEventoRepository,
        processar_webhook_pedido: ProcessarWebhookPedidoUseCase,
        backoff: BackoffWebhookEmMemoria | None = None,
    ) -> None:
        self._webhook_eventos = webhook_evento_repository
        self._processar_webhook_pedido = processar_webhook_pedido
        # Sem um `backoff` injetado (ex.: uso pontual/teste), cria um próprio —
        # mas então o estado só vive enquanto ESTA instância viver.
        self._backoff = backoff if backoff is not None else BackoffWebhookEmMemoria()

    async def executar(
        self,
        *,
        limite: int = LIMITE_LOTE_PADRAO,
        confirmar_apos_cada_evento: Callable[[], Awaitable[None]] = _noop,
        reverter_apos_erro: Callable[[], Awaitable[None]] = _noop,
    ) -> int:
        """Consome até `limite` eventos pendentes (`PENDENTE`/`ERRO`, mais
        antigos primeiro, `FOR UPDATE SKIP LOCKED`) e retorna quantos foram
        TRATADOS — processados (com qualquer desfecho), ignorados por tipo ou
        escalados por teto de tentativas. Eventos ainda em janela de backoff
        são pulados: não contam e não são marcados.

        `confirmar_apos_cada_evento` (ex.: `session.commit()`) é chamado
        depois de CADA evento tratado, antes de tentar o próximo — mesma razão
        de `ReconciliarPedidosUseCase.executar`: `VendasIntegracaoGateway.
        confirmar_pedido_externo` faz um `session.rollback()` completo (não um
        SAVEPOINT) ao traduzir um `IntegrityError` em
        `PedidoExternoJaProcessado`, o que desfaria o `webhook_evento`
        `PROCESSADO` de eventos anteriores deste mesmo lote ainda não
        persistidos. Consequência conhecida: o primeiro commit também libera
        os `FOR UPDATE` dos demais eventos do lote; com mais de uma réplica do
        worker dois processos poderiam pegar o mesmo evento — inofensivo (a
        idempotência de `pedido.UNIQUE(origem_canal, pedido_externo_id)`
        transforma o segundo em `PedidoExternoJaProcessado`), e hoje há 1
        réplica (design §4.5).

        `reverter_apos_erro` (ex.: `session.rollback()`) é chamado quando um
        evento levanta uma exceção inesperada: se ela veio do banco, a
        transação está abortada e nada mais funciona (nem o `marcar_erro`
        que vem a seguir) até um rollback. Ambos os parâmetros são opcionais
        (default no-op) para este caso de uso continuar sem conhecer
        SQLAlchemy — `run_worker.py` é quem passa `session.commit`/
        `session.rollback`."""
        if limite <= 0:
            return 0

        self._backoff.podar_expirados()
        # Cada evento em janela de backoff ocupa uma vaga do `SELECT ... LIMIT`
        # mas é pulado — sem esta folga, `limite` eventos envenenados em
        # backoff (os mais antigos, `ORDER BY recebido_em`) impediriam eventos
        # novos de chegarem ao lote (head-of-line blocking).
        eventos = await self._webhook_eventos.buscar_lote_pendente(
            limite=limite + len(self._backoff)
        )

        tratados = 0
        for evento in eventos:
            if tratados >= limite:
                break
            if not await self._tratar_evento(evento, reverter_apos_erro):
                continue
            await confirmar_apos_cada_evento()
            tratados += 1
        return tratados

    async def _tratar_evento(
        self, evento: WebhookEvento, reverter_apos_erro: Callable[[], Awaitable[None]]
    ) -> bool:
        """`False` se o evento foi pulado (janela de backoff); `True` se foi
        tratado por qualquer outro desfecho."""
        if evento.tipo_evento not in TIPOS_EVENTO_PROCESSAVEIS:
            await self._ignorar(evento)
            return True

        if evento.tentativas >= MAX_TENTATIVAS_WEBHOOK:
            # Antes do teste de backoff: um evento que acabou de esgotar o
            # teto deve ser escalado já no próximo tick, não depois de mais
            # uma espera.
            await self._escalar_por_teto_de_tentativas(evento)
            return True

        if self._backoff.em_janela(evento.id):
            return False

        try:
            await self._processar_webhook_pedido.executar(evento)
        except Exception as exc:  # noqa: BLE001 — 1 evento com falha nunca derruba o lote
            await self._registrar_falha_inesperada(evento, exc, reverter_apos_erro)

        # Registrado APÓS a tentativa e independentemente do desfecho:
        # `ProcessarWebhookPedidoUseCase.executar` devolve `None` e não diz se
        # terminou em `marcar_erro`. Para quem terminou `PROCESSADO`/
        # `CONFLITO_MANUAL` a entrada é inócua (o evento nunca mais aparece em
        # `buscar_lote_pendente`) e é podada ao expirar.
        self._backoff.registrar_tentativa(evento.id, tentativas_apos_falha=evento.tentativas + 1)
        return True

    async def _ignorar(self, evento: WebhookEvento) -> None:
        _logger.warning(
            "webhook_evento.ignorado",
            evento_externo_id=evento.evento_externo_id,
            tipo_evento=evento.tipo_evento,
        )
        await self._webhook_eventos.marcar_processado(evento.id)

    async def _escalar_por_teto_de_tentativas(self, evento: WebhookEvento) -> None:
        ultimo_erro = evento.erro_detalhe or "(sem detalhe registrado)"
        detalhe = (
            f"teto de {MAX_TENTATIVAS_WEBHOOK} tentativas esgotado; último erro: {ultimo_erro}"
        )
        await self._webhook_eventos.marcar_conflito_manual(evento.id, detalhe=detalhe)
        _logger.error(
            "webhook_evento.conflito_manual",
            evento_externo_id=evento.evento_externo_id,
            motivo="teto_tentativas_esgotado",
            tentativas=evento.tentativas,
            detalhe=detalhe,
        )

    async def _registrar_falha_inesperada(
        self,
        evento: WebhookEvento,
        exc: Exception,
        reverter_apos_erro: Callable[[], Awaitable[None]],
    ) -> None:
        # Traceback completo no log (necessário para diagnosticar um evento
        # envenenado); o payload do evento nunca é logado por este módulo.
        _logger.exception(
            "webhook_evento.erro_inesperado",
            evento_externo_id=evento.evento_externo_id,
            tipo_evento=evento.tipo_evento,
            erro_tipo=type(exc).__name__,
        )
        detalhe = f"erro inesperado ({type(exc).__name__}): {exc}"[:_DETALHE_MAX_CARACTERES]
        try:
            # Primeiro o rollback: se a exceção veio do banco, a transação está
            # abortada e o `marcar_erro` abaixo falharia com
            # `InFailedSQLTransactionError`. O rollback também descarta
            # escritas parciais deste evento; os anteriores já foram
            # confirmados por `confirmar_apos_cada_evento`.
            await reverter_apos_erro()
            await self._webhook_eventos.marcar_erro(evento.id, detalhe=detalhe)
        except Exception:
            _logger.exception(
                "webhook_evento.erro_ao_registrar_falha",
                evento_externo_id=evento.evento_externo_id,
            )
            # Deixa a sessão utilizável para os próximos eventos do lote; o
            # evento segue `PENDENTE`/`ERRO` no banco e será retentado após o
            # backoff em memória.
            try:
                await reverter_apos_erro()
            except Exception:
                _logger.exception(
                    "webhook_evento.erro_ao_reverter",
                    evento_externo_id=evento.evento_externo_id,
                )
