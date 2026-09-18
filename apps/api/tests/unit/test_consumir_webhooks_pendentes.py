"""Testes unitários de `ConsumirWebhooksPendentesUseCase` e
`BackoffWebhookEmMemoria` (fakes em memória, sem I/O) — ver
docs/design-integracao-nuvemshop.md §4.5/§5.3.

O relógio é injetado (`_Relogio`) e o jitter é neutralizado por
`monkeypatch` (`calcular_backoff_segundos` -> `2**tentativa`, exato), então
nenhum teste dorme nem depende de sorte."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest
from structlog.testing import capture_logs

from amactive.contexts.integracao_canais.application.use_cases import (
    consumir_webhooks_pendentes as modulo,
)
from amactive.contexts.integracao_canais.application.use_cases.consumir_webhooks_pendentes import (
    BACKOFF_MAXIMO_SEGUNDOS,
    MAX_TENTATIVAS_WEBHOOK,
    BackoffWebhookEmMemoria,
    ConsumirWebhooksPendentesUseCase,
)
from amactive.contexts.integracao_canais.domain.entities import (
    CanalIntegracao,
    StatusWebhookEvento,
    WebhookEvento,
)

pytestmark = pytest.mark.unit


class _Relogio:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += segundos


class _Trilha:
    """Registra a ordem das chamadas de infraestrutura (rollback/commit/
    marcar_erro) para asserções de sequência."""

    def __init__(self) -> None:
        self.passos: list[str] = []
        self.commits = 0
        self.rollbacks = 0

    async def confirmar(self) -> None:
        self.commits += 1
        self.passos.append("confirmar")

    async def reverter(self) -> None:
        self.rollbacks += 1
        self.passos.append("reverter")


class _WebhookRepoFake:
    """Fake de `WebhookEventoRepository` — ordem de inserção = ordem de
    `recebido_em`; só `PENDENTE`/`ERRO` voltam de `buscar_lote_pendente`."""

    def __init__(self, eventos: list[WebhookEvento], trilha: _Trilha | None = None) -> None:
        self.eventos: dict[uuid.UUID, WebhookEvento] = {e.id: e for e in eventos}
        self.limites_pedidos: list[int] = []
        self.falhar_marcar_erro = False
        self._trilha = trilha

    def adicionar(self, evento: WebhookEvento) -> None:
        self.eventos[evento.id] = evento

    def por_recurso(self, id_recurso_externo: str) -> WebhookEvento:
        return next(e for e in self.eventos.values() if e.id_recurso_externo == id_recurso_externo)

    async def buscar_lote_pendente(self, *, limite: int) -> list[WebhookEvento]:
        self.limites_pedidos.append(limite)
        pendentes = [
            e
            for e in self.eventos.values()
            if e.status in (StatusWebhookEvento.PENDENTE, StatusWebhookEvento.ERRO)
        ]
        return pendentes[:limite]

    async def marcar_processado(self, evento_id: uuid.UUID) -> None:
        self.eventos[evento_id] = replace(
            self.eventos[evento_id], status=StatusWebhookEvento.PROCESSADO
        )

    async def marcar_erro(self, evento_id: uuid.UUID, *, detalhe: str) -> None:
        if self._trilha is not None:
            self._trilha.passos.append("marcar_erro")
        if self.falhar_marcar_erro:
            raise RuntimeError("banco indisponível")
        atual = self.eventos[evento_id]
        self.eventos[evento_id] = replace(
            atual,
            status=StatusWebhookEvento.ERRO,
            tentativas=atual.tentativas + 1,
            erro_detalhe=detalhe,
        )

    async def marcar_conflito_manual(self, evento_id: uuid.UUID, *, detalhe: str) -> None:
        self.eventos[evento_id] = replace(
            self.eventos[evento_id],
            status=StatusWebhookEvento.CONFLITO_MANUAL,
            erro_detalhe=detalhe,
        )

    async def contar_pendentes(self) -> int:
        return len(await self.buscar_lote_pendente(limite=1_000_000))


class _ProcessadorFake:
    """Fake de `ProcessarWebhookPedidoUseCase` — o desfecho de cada evento é
    escolhido por `id_recurso_externo` (`"ok"` por padrão), mutável entre
    chamadas de `executar` do use case sob teste."""

    def __init__(self, repo: _WebhookRepoFake) -> None:
        self._repo = repo
        self.acoes: dict[str, str] = {}
        self.chamadas: list[str] = []

    async def executar(self, evento: WebhookEvento) -> None:
        self.chamadas.append(evento.id_recurso_externo)
        acao = self.acoes.get(evento.id_recurso_externo, "ok")
        if acao == "ok":
            await self._repo.marcar_processado(evento.id)
        elif acao == "erro":
            await self._repo.marcar_erro(evento.id, detalhe="nuvemshop fora do ar")
        elif acao == "explode":
            raise RuntimeError("boom")
        else:  # pragma: no cover — proteção contra typo em teste
            raise AssertionError(f"ação desconhecida: {acao}")


def _evento(
    id_recurso: str,
    *,
    tipo: str = "order/paid",
    status: StatusWebhookEvento = StatusWebhookEvento.PENDENTE,
    tentativas: int = 0,
    erro_detalhe: str | None = None,
) -> WebhookEvento:
    return WebhookEvento(
        id=uuid.uuid4(),
        canal=CanalIntegracao.NUVEMSHOP,
        evento_externo_id=f"NUVEMSHOP:{tipo}:{id_recurso}",
        tipo_evento=tipo,
        id_recurso_externo=id_recurso,
        payload_bruto={"id": id_recurso, "cliente_email": "segredo@example.com"},
        status=status,
        tentativas=tentativas,
        erro_detalhe=erro_detalhe,
        recebido_em=datetime.now(UTC),
        processado_em=None,
    )


class _Cenario:
    def __init__(self, eventos: list[WebhookEvento]) -> None:
        self.relogio = _Relogio()
        self.trilha = _Trilha()
        self.repo = _WebhookRepoFake(eventos, self.trilha)
        self.processador = _ProcessadorFake(self.repo)
        self.backoff = BackoffWebhookEmMemoria(relogio=self.relogio)

    def use_case(self) -> ConsumirWebhooksPendentesUseCase:
        # Uma instância NOVA a cada chamada, todas compartilhando o mesmo
        # `backoff` — exatamente como `run_worker.py` faz a cada tick.
        return ConsumirWebhooksPendentesUseCase(
            webhook_evento_repository=self.repo,  # type: ignore[arg-type]
            processar_webhook_pedido=self.processador,  # type: ignore[arg-type]
            backoff=self.backoff,
        )

    async def executar(self, **kwargs: Any) -> int:
        return await self.use_case().executar(
            confirmar_apos_cada_evento=self.trilha.confirmar,
            reverter_apos_erro=self.trilha.reverter,
            **kwargs,
        )


@pytest.fixture(autouse=True)
def _backoff_sem_jitter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(modulo, "calcular_backoff_segundos", lambda tentativa: 2.0**tentativa)


# ── (vii) lote vazio ──
async def test_lote_vazio_e_noop_e_retorna_zero() -> None:
    cenario = _Cenario([])

    tratados = await cenario.executar()

    assert tratados == 0
    assert cenario.processador.chamadas == []
    assert cenario.trilha.commits == 0


async def test_limite_nao_positivo_nem_consulta_o_repositorio() -> None:
    cenario = _Cenario([_evento("1")])

    assert await cenario.executar(limite=0) == 0
    assert cenario.repo.limites_pedidos == []


# ── (i) tipos processáveis ──
@pytest.mark.parametrize("tipo", ["order/paid", "reconciliacao"])
async def test_tipos_processaveis_vao_para_o_processador(tipo: str) -> None:
    cenario = _Cenario([_evento("1", tipo=tipo)])

    tratados = await cenario.executar()

    assert tratados == 1
    assert cenario.processador.chamadas == ["1"]
    assert cenario.repo.por_recurso("1").status == StatusWebhookEvento.PROCESSADO


# ── (ii) tipo desconhecido nunca vira pedido ──
async def test_tipo_desconhecido_nunca_chama_processador_e_e_marcado_processado() -> None:
    cenario = _Cenario([_evento("1", tipo="order/cancelled")])

    with capture_logs() as logs:
        tratados = await cenario.executar()

    assert tratados == 1
    assert cenario.processador.chamadas == []
    assert cenario.repo.por_recurso("1").status == StatusWebhookEvento.PROCESSADO

    (ignorado,) = [entrada for entrada in logs if entrada["event"] == "webhook_evento.ignorado"]
    assert ignorado["log_level"] == "warning"
    assert ignorado["evento_externo_id"] == "NUVEMSHOP:order/cancelled:1"
    assert ignorado["tipo_evento"] == "order/cancelled"
    # nunca o payload (dados pessoais do comprador)
    assert "segredo@example.com" not in repr(logs)
    assert not any("payload" in chave for entrada in logs for chave in entrada)


# ── (iv) teto de tentativas ──
async def test_teto_de_tentativas_escala_para_conflito_manual_sem_chamar_processador() -> None:
    cenario = _Cenario(
        [
            _evento(
                "1",
                status=StatusWebhookEvento.ERRO,
                tentativas=MAX_TENTATIVAS_WEBHOOK,
                erro_detalhe="nuvemshop fora do ar",
            )
        ]
    )

    with capture_logs() as logs:
        tratados = await cenario.executar()

    assert tratados == 1
    assert cenario.processador.chamadas == []
    evento = cenario.repo.por_recurso("1")
    assert evento.status == StatusWebhookEvento.CONFLITO_MANUAL
    assert evento.erro_detalhe == (
        "teto de 12 tentativas esgotado; último erro: nuvemshop fora do ar"
    )
    (erro,) = [e for e in logs if e["event"] == "webhook_evento.conflito_manual"]
    assert erro["log_level"] == "error"
    assert erro["motivo"] == "teto_tentativas_esgotado"


async def test_uma_tentativa_abaixo_do_teto_ainda_e_processada() -> None:
    cenario = _Cenario(
        [_evento("1", status=StatusWebhookEvento.ERRO, tentativas=MAX_TENTATIVAS_WEBHOOK - 1)]
    )

    await cenario.executar()

    assert cenario.processador.chamadas == ["1"]
    assert cenario.repo.por_recurso("1").status == StatusWebhookEvento.PROCESSADO


async def test_teto_esgotado_e_escalado_mesmo_dentro_de_janela_de_backoff() -> None:
    cenario = _Cenario([_evento("1")])
    cenario.processador.acoes["1"] = "erro"
    # leva o evento a `tentativas == MAX` reprocessando após cada janela
    for _ in range(MAX_TENTATIVAS_WEBHOOK):
        assert await cenario.executar() == 1
        cenario.relogio.avancar(BACKOFF_MAXIMO_SEGUNDOS + 1)
    assert cenario.repo.por_recurso("1").tentativas == MAX_TENTATIVAS_WEBHOOK
    # a última falha acabou de abrir uma janela; ainda assim escala já
    cenario.backoff.registrar_tentativa(
        cenario.repo.por_recurso("1").id, tentativas_apos_falha=MAX_TENTATIVAS_WEBHOOK
    )

    assert await cenario.executar() == 1

    assert cenario.repo.por_recurso("1").status == StatusWebhookEvento.CONFLITO_MANUAL
    assert len(cenario.processador.chamadas) == MAX_TENTATIVAS_WEBHOOK


# ── (iii) backoff ──
async def test_evento_em_janela_de_backoff_e_pulado_e_depois_reprocessado() -> None:
    cenario = _Cenario([_evento("1")])
    cenario.processador.acoes["1"] = "erro"

    assert await cenario.executar() == 1  # 1ª falha -> tentativas=1 -> espera 2s
    assert cenario.repo.por_recurso("1").tentativas == 1

    assert await cenario.executar() == 0  # dentro da janela: pulado, não conta
    cenario.relogio.avancar(1.9)
    assert await cenario.executar() == 0
    assert cenario.processador.chamadas == ["1"]
    assert cenario.repo.por_recurso("1").tentativas == 1  # nem marcado

    cenario.processador.acoes["1"] = "ok"
    cenario.relogio.avancar(0.2)  # 2.1s depois da falha: janela vencida
    assert await cenario.executar() == 1

    assert cenario.processador.chamadas == ["1", "1"]
    assert cenario.repo.por_recurso("1").status == StatusWebhookEvento.PROCESSADO


async def test_backoff_dobra_a_cada_falha_consecutiva() -> None:
    cenario = _Cenario([_evento("1")])
    cenario.processador.acoes["1"] = "erro"

    await cenario.executar()  # tentativas=1 -> 2s
    cenario.relogio.avancar(2.1)
    await cenario.executar()  # tentativas=2 -> 4s
    assert cenario.repo.por_recurso("1").tentativas == 2

    cenario.relogio.avancar(3.9)
    assert await cenario.executar() == 0
    cenario.relogio.avancar(0.2)
    assert await cenario.executar() == 1
    assert cenario.repo.por_recurso("1").tentativas == 3


async def test_espera_de_backoff_tem_teto() -> None:
    cenario = _Cenario([_evento("1", status=StatusWebhookEvento.ERRO, tentativas=10)])
    cenario.processador.acoes["1"] = "erro"

    await cenario.executar()  # tentativas=11 -> 2**11 = 2048s, limitado a 300s
    assert cenario.repo.por_recurso("1").tentativas == 11

    cenario.relogio.avancar(BACKOFF_MAXIMO_SEGUNDOS - 1)
    assert await cenario.executar() == 0
    cenario.relogio.avancar(2)
    assert await cenario.executar() == 1


async def test_backoff_sobrevive_entre_instancias_do_use_case() -> None:
    cenario = _Cenario([_evento("1")])
    cenario.processador.acoes["1"] = "erro"

    await cenario.use_case().executar()  # "tick 1"
    # "tick 2": use case NOVO (como `run_worker.py` recria por tick), mesmo backoff
    assert await cenario.use_case().executar() == 0
    assert cenario.processador.chamadas == ["1"]


async def test_use_case_sem_backoff_injetado_cria_o_proprio() -> None:
    cenario = _Cenario([_evento("1")])
    cenario.processador.acoes["1"] = "erro"
    use_case = ConsumirWebhooksPendentesUseCase(
        webhook_evento_repository=cenario.repo,  # type: ignore[arg-type]
        processar_webhook_pedido=cenario.processador,  # type: ignore[arg-type]
    )

    assert await use_case.executar() == 1
    assert await use_case.executar() == 0  # já em janela (relógio real, 2s)


async def test_eventos_em_backoff_nao_bloqueiam_eventos_novos_do_lote() -> None:
    cenario = _Cenario([_evento("velho-1"), _evento("velho-2")])
    cenario.processador.acoes.update({"velho-1": "erro", "velho-2": "erro"})
    assert await cenario.executar(limite=2) == 2  # ambos em backoff agora

    cenario.repo.adicionar(_evento("novo-1"))
    cenario.repo.adicionar(_evento("novo-2"))
    tratados = await cenario.executar(limite=2)

    # Sem a folga no `LIMIT`, o SELECT devolveria só os 2 velhos (mais
    # antigos primeiro), ambos pulados, e os novos ficariam à míngua.
    assert tratados == 2
    assert cenario.repo.por_recurso("novo-1").status == StatusWebhookEvento.PROCESSADO
    assert cenario.repo.por_recurso("novo-2").status == StatusWebhookEvento.PROCESSADO
    assert cenario.repo.limites_pedidos[-1] == 2 + 2


async def test_limite_restringe_quantos_eventos_sao_tratados_no_tick() -> None:
    cenario = _Cenario([_evento(str(i)) for i in range(5)])

    assert await cenario.executar(limite=2) == 2
    assert cenario.processador.chamadas == ["0", "1"]
    assert await cenario.executar(limite=2) == 2
    assert cenario.processador.chamadas == ["0", "1", "2", "3"]


# ── (v) exceção inesperada isolada ──
async def test_excecao_inesperada_num_evento_nao_impede_o_seguinte() -> None:
    cenario = _Cenario([_evento("1"), _evento("2")])
    cenario.processador.acoes["1"] = "explode"

    with capture_logs() as logs:
        tratados = await cenario.executar()

    assert tratados == 2
    assert cenario.processador.chamadas == ["1", "2"]

    falho = cenario.repo.por_recurso("1")
    assert falho.status == StatusWebhookEvento.ERRO
    assert falho.tentativas == 1
    assert falho.erro_detalhe is not None
    assert "RuntimeError" in falho.erro_detalhe and "boom" in falho.erro_detalhe
    assert cenario.repo.por_recurso("2").status == StatusWebhookEvento.PROCESSADO

    # rollback ANTES do marcar_erro (transação possivelmente abortada) e um
    # commit por evento tratado, incluindo o que falhou.
    assert cenario.trilha.passos == ["reverter", "marcar_erro", "confirmar", "confirmar"]
    (inesperado,) = [e for e in logs if e["event"] == "webhook_evento.erro_inesperado"]
    assert inesperado["log_level"] == "error"
    assert inesperado["erro_tipo"] == "RuntimeError"
    assert inesperado["evento_externo_id"] == "NUVEMSHOP:order/paid:1"


async def test_excecao_inesperada_segue_o_mesmo_backoff_dos_demais_erros() -> None:
    cenario = _Cenario([_evento("1")])
    cenario.processador.acoes["1"] = "explode"

    assert await cenario.executar() == 1
    assert await cenario.executar() == 0  # em janela
    cenario.relogio.avancar(2.1)
    assert await cenario.executar() == 1
    assert cenario.processador.chamadas == ["1", "1"]


async def test_falha_ao_registrar_a_falha_tambem_nao_derruba_o_lote() -> None:
    cenario = _Cenario([_evento("1"), _evento("2")])
    cenario.processador.acoes["1"] = "explode"
    cenario.repo.falhar_marcar_erro = True

    with capture_logs() as logs:
        tratados = await cenario.executar()

    assert tratados == 2
    assert cenario.repo.por_recurso("2").status == StatusWebhookEvento.PROCESSADO
    # sem `marcar_erro` possível, continua PENDENTE — mas em backoff em memória
    assert cenario.repo.por_recurso("1").status == StatusWebhookEvento.PENDENTE
    assert await cenario.executar() == 0
    assert any(e["event"] == "webhook_evento.erro_ao_registrar_falha" for e in logs)
    # rollback antes do marcar_erro e de novo após ele falhar (sessão limpa
    # para o evento seguinte)
    assert cenario.trilha.rollbacks == 2


# ── (vi) callback de confirmação ──
async def test_confirmar_e_chamado_uma_vez_por_evento_tratado_e_nunca_para_pulado() -> None:
    cenario = _Cenario(
        [
            _evento("ok"),
            _evento("ignorado", tipo="order/cancelled"),
            _evento("teto", status=StatusWebhookEvento.ERRO, tentativas=MAX_TENTATIVAS_WEBHOOK),
            _evento("explode"),
            _evento("em-backoff"),
        ]
    )
    cenario.processador.acoes.update({"explode": "explode", "em-backoff": "erro"})

    assert await cenario.executar() == 5
    assert cenario.trilha.commits == 5

    # 2º tick: só `explode` e `em-backoff` continuam pendentes, ambos em janela.
    assert await cenario.executar() == 0
    assert cenario.trilha.commits == 5


# ── BackoffWebhookEmMemoria ──
def test_backoff_sem_registro_nao_esta_em_janela() -> None:
    assert BackoffWebhookEmMemoria().em_janela(uuid.uuid4()) is False


def test_backoff_janela_vence_e_e_podada() -> None:
    relogio = _Relogio()
    backoff = BackoffWebhookEmMemoria(relogio=relogio)
    evento_id = uuid.uuid4()

    espera = backoff.registrar_tentativa(evento_id, tentativas_apos_falha=3)

    assert espera == 8.0  # 2**3, sem jitter (monkeypatch)
    assert backoff.em_janela(evento_id) is True
    assert len(backoff) == 1
    relogio.avancar(8.0)
    assert backoff.em_janela(evento_id) is False
    backoff.podar_expirados()
    assert len(backoff) == 0


def test_backoff_tentativas_nao_positivas_usam_o_menor_degrau() -> None:
    assert (
        BackoffWebhookEmMemoria().registrar_tentativa(uuid.uuid4(), tentativas_apos_falha=0) == 2.0
    )


def test_backoff_real_tem_jitter_de_20_por_cento_e_teto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()  # volta a usar `calcular_backoff_segundos` de verdade
    backoff = BackoffWebhookEmMemoria()

    esperas_1 = [
        backoff.registrar_tentativa(uuid.uuid4(), tentativas_apos_falha=1) for _ in range(200)
    ]
    esperas_12 = [
        backoff.registrar_tentativa(uuid.uuid4(), tentativas_apos_falha=12) for _ in range(50)
    ]

    assert all(1.6 <= espera <= 2.4 for espera in esperas_1)
    assert len(set(esperas_1)) > 1  # há jitter
    assert all(espera == BACKOFF_MAXIMO_SEGUNDOS for espera in esperas_12)


def test_constantes_publicas_do_consumo() -> None:
    assert MAX_TENTATIVAS_WEBHOOK == 12
    assert modulo.TIPOS_EVENTO_PROCESSAVEIS == {"order/paid", "reconciliacao"}
