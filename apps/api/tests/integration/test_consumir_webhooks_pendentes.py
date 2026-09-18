"""Teste de integração de `ConsumirWebhooksPendentesUseCase` (Postgres real,
`NuvemshopClientPort` fake por injeção de dependência — nunca uma chamada
HTTP real) — ver docs/design-integracao-nuvemshop.md §4.5/§5.3/§9 passo 7.

Reproduz o que `scripts/run_worker.py` monta a cada tick: o mesmo
`ProcessarWebhookPedidoUseCase` real (gateways + repositórios sobre a
sessão), `session.commit`/`session.rollback` como callbacks e um
`BackoffWebhookEmMemoria` compartilhado entre "ticks" (aqui, chamadas
sucessivas de `_tick`). Os cenários unitários exaustivos (fakes em memória)
estão em `tests/unit/test_consumir_webhooks_pendentes.py`."""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from prometheus_client import REGISTRY
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel
from amactive.contexts.integracao_canais.application.use_cases.consumir_webhooks_pendentes import (
    MAX_TENTATIVAS_WEBHOOK,
    BackoffWebhookEmMemoria,
    ConsumirWebhooksPendentesUseCase,
)
from amactive.contexts.integracao_canais.application.use_cases.processar_webhook_pedido import (
    ProcessarWebhookPedidoUseCase,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao, WebhookEvento
from amactive.contexts.integracao_canais.domain.exceptions import NuvemshopIndisponivel
from amactive.contexts.integracao_canais.domain.repositories import (
    ItemPedidoExternoDTO,
    NuvemshopPedidoDTO,
    ProdutoParaPublicacao,
    PublicacaoResultado,
)
from amactive.contexts.integracao_canais.infrastructure.gateways.cadastros_gateway import (
    CadastrosIntegracaoGateway,
)
from amactive.contexts.integracao_canais.infrastructure.gateways.vendas_gateway import (
    EMAIL_USUARIO_INTEGRACAO,
    VendasIntegracaoGateway,
    resetar_cache_usuario_integracao_para_testes,
)
from amactive.contexts.integracao_canais.infrastructure.persistence.repositories import (
    SqlAlchemyMapeamentoVarianteRepository,
    SqlAlchemyWebhookEventoRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _cache_usuario_integracao_isolado():
    """Ver mesma justificativa em `test_processar_webhook_pedido.py`."""
    resetar_cache_usuario_integracao_para_testes()
    yield
    resetar_cache_usuario_integracao_para_testes()


@pytest.fixture
async def usuario_integracao(db_session: AsyncSession) -> UsuarioModel:
    usuario = UsuarioModel(
        id=uuid.uuid4(),
        nome="Integração Nuvemshop (sistema)",
        email=EMAIL_USUARIO_INTEGRACAO,
        senha_hash="hash-nao-usado-neste-teste",
        papel="VENDEDOR",
        ativo=False,
        criado_em=datetime.now(UTC),
    )
    db_session.add(usuario)
    await db_session.commit()
    return usuario


class _Relogio:
    def __init__(self) -> None:
        self.agora = 5000.0

    def __call__(self) -> float:
        return self.agora

    def avancar(self, segundos: float) -> None:
        self.agora += segundos


class _NuvemshopClientFake:
    """Fake de `NuvemshopClientPort` — só `buscar_pedido` é exercido. Um id
    fora de `pedidos` levanta `AssertionError` (o teste não esperava essa
    chamada); `falhas`/`ganchos` injetam, por id, uma exceção ou um efeito
    colateral antes de responder."""

    def __init__(self, pedidos: dict[str, NuvemshopPedidoDTO] | None = None) -> None:
        self.pedidos = pedidos or {}
        self.chamadas: list[str] = []
        self.falhas: dict[str, Exception] = {}
        self.ganchos: dict[str, Callable[[], Awaitable[None]]] = {}

    async def buscar_pedido(self, pedido_externo_id: str) -> NuvemshopPedidoDTO:
        self.chamadas.append(pedido_externo_id)
        if pedido_externo_id in self.ganchos:
            await self.ganchos[pedido_externo_id]()
        if pedido_externo_id in self.falhas:
            raise self.falhas[pedido_externo_id]
        if pedido_externo_id not in self.pedidos:
            raise AssertionError(f"buscar_pedido('{pedido_externo_id}') inesperado neste teste.")
        return self.pedidos[pedido_externo_id]

    async def criar_produto(self, produto: ProdutoParaPublicacao) -> PublicacaoResultado:
        raise NotImplementedError

    async def atualizar_produto(
        self, produto_externo_id: str, produto: ProdutoParaPublicacao
    ) -> PublicacaoResultado:
        raise NotImplementedError

    async def atualizar_estoque_variante(
        self, *, produto_externo_id: str, variante_externo_id: str, quantidade: int
    ) -> None:
        raise NotImplementedError

    async def listar_pedidos_recentes(self, *, desde: datetime) -> list[str]:
        raise NotImplementedError


def _pedido_dto(
    pedido_externo_id: str, *, variante_externo_id: str, valor: str
) -> NuvemshopPedidoDTO:
    return NuvemshopPedidoDTO(
        pedido_externo_id=pedido_externo_id,
        cliente_email=f"{pedido_externo_id}@example.com",
        cliente_nome="Cliente Consumo",
        cliente_cpf_cnpj=None,
        cliente_telefone=None,
        cliente_endereco=None,
        cliente_externo_id=f"cliente-{pedido_externo_id}",
        itens=[
            ItemPedidoExternoDTO(
                variante_externo_id=variante_externo_id,
                produto_externo_id=f"p-{variante_externo_id}",
                quantidade=1,
            )
        ],
        valor_total=Decimal(valor),
    )


async def _mapear_variante(
    db_session: AsyncSession, criar_variante_com_estoque, *, variante_externo_id: str
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="49.90")
    await SqlAlchemyMapeamentoVarianteRepository(db_session).upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id=f"p-{variante_externo_id}",
        variante_externo_id=variante_externo_id,
    )
    await db_session.commit()


async def _registrar_evento(
    db_session: AsyncSession, *, id_recurso_externo: str, tipo_evento: str = "order/paid"
) -> WebhookEvento:
    evento = await SqlAlchemyWebhookEventoRepository(db_session).registrar_se_novo(
        canal=CanalIntegracao.NUVEMSHOP,
        tipo_evento=tipo_evento,
        id_recurso_externo=id_recurso_externo,
        payload_bruto={"id": id_recurso_externo, "event": tipo_evento},
    )
    assert evento is not None
    await db_session.commit()
    return evento


async def _tick(
    db_session: AsyncSession,
    client: _NuvemshopClientFake,
    backoff: BackoffWebhookEmMemoria,
    *,
    limite: int = 10,
) -> int:
    """Equivalente a `run_worker._processar_webhooks`: use case novo (e
    repositórios/gateways novos) a cada chamada, só o `backoff` é reaproveitado."""
    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    processar = ProcessarWebhookPedidoUseCase(
        nuvemshop_client=client,
        cliente_integracao=CadastrosIntegracaoGateway(db_session),
        mapeamento_variante_repository=SqlAlchemyMapeamentoVarianteRepository(db_session),
        pedido_integracao=VendasIntegracaoGateway(db_session),
        webhook_evento_repository=webhook_repo,
    )
    use_case = ConsumirWebhooksPendentesUseCase(
        webhook_evento_repository=webhook_repo,
        processar_webhook_pedido=processar,
        backoff=backoff,
    )
    return await use_case.executar(
        limite=limite,
        confirmar_apos_cada_evento=db_session.commit,
        reverter_apos_erro=db_session.rollback,
    )


async def _status_evento(db_session: AsyncSession, evento: WebhookEvento) -> str:
    status = await db_session.scalar(
        text("SELECT status FROM webhook_evento WHERE id = :id"), {"id": evento.id}
    )
    return str(status)


async def _total_pedidos(db_session: AsyncSession, pedido_externo_id: str) -> int:
    total = await db_session.scalar(
        text("SELECT count(*) FROM pedido WHERE pedido_externo_id = :id"),
        {"id": pedido_externo_id},
    )
    return int(total or 0)


# ── (i) order/paid PENDENTE -> pedido + PROCESSADO ──
async def test_evento_order_paid_pendente_vira_pedido_e_processado(
    db_session: AsyncSession, usuario_integracao: UsuarioModel, criar_variante_com_estoque
) -> None:
    await _mapear_variante(
        db_session, criar_variante_com_estoque, variante_externo_id="v-consumo-1"
    )
    evento = await _registrar_evento(db_session, id_recurso_externo="consumo-pago-1")
    client = _NuvemshopClientFake(
        {
            "consumo-pago-1": _pedido_dto(
                "consumo-pago-1", variante_externo_id="v-consumo-1", valor="49.90"
            )
        }
    )

    tratados = await _tick(db_session, client, BackoffWebhookEmMemoria())

    assert tratados == 1
    assert await _status_evento(db_session, evento) == "PROCESSADO"
    pedido = (
        (
            await db_session.execute(
                text(
                    "SELECT status, origem_canal FROM pedido "
                    "WHERE pedido_externo_id = 'consumo-pago-1'"
                )
            )
        )
        .mappings()
        .one()
    )
    assert pedido["status"] == "CONFIRMADO"
    assert pedido["origem_canal"] == "NUVEMSHOP"


# ── (ii) tipo desconhecido -> PROCESSADO, zero pedidos ──
async def test_tipo_desconhecido_e_processado_sem_criar_pedido_nem_chamar_a_nuvemshop(
    db_session: AsyncSession, usuario_integracao: UsuarioModel
) -> None:
    evento = await _registrar_evento(
        db_session, id_recurso_externo="consumo-cancelado-1", tipo_evento="order/cancelled"
    )
    client = _NuvemshopClientFake()  # qualquer `buscar_pedido` seria AssertionError

    tratados = await _tick(db_session, client, BackoffWebhookEmMemoria())

    assert tratados == 1
    assert client.chamadas == []
    assert await _status_evento(db_session, evento) == "PROCESSADO"
    assert await _total_pedidos(db_session, "consumo-cancelado-1") == 0


# ── (iii) ERRO em janela de backoff é pulado; depois da janela é reprocessado ──
async def test_evento_erro_em_backoff_e_pulado_e_depois_da_janela_e_reprocessado(
    db_session: AsyncSession, usuario_integracao: UsuarioModel, criar_variante_com_estoque
) -> None:
    await _mapear_variante(
        db_session, criar_variante_com_estoque, variante_externo_id="v-consumo-2"
    )
    evento = await _registrar_evento(db_session, id_recurso_externo="consumo-backoff-1")
    client = _NuvemshopClientFake(
        {
            "consumo-backoff-1": _pedido_dto(
                "consumo-backoff-1", variante_externo_id="v-consumo-2", valor="49.90"
            )
        }
    )
    client.falhas["consumo-backoff-1"] = NuvemshopIndisponivel("Nuvemshop fora do ar")
    relogio = _Relogio()
    backoff = BackoffWebhookEmMemoria(relogio=relogio)

    assert await _tick(db_session, client, backoff) == 1  # 1ª falha -> ERRO, tentativas=1
    assert await _status_evento(db_session, evento) == "ERRO"

    # dentro da janela (2s ±20% => mínimo 1.6s): pulado, sem nova chamada nem tentativa
    relogio.avancar(1.0)
    assert await _tick(db_session, client, backoff) == 0
    assert client.chamadas == ["consumo-backoff-1"]
    tentativas = await db_session.scalar(
        text("SELECT tentativas FROM webhook_evento WHERE id = :id"), {"id": evento.id}
    )
    assert tentativas == 1

    # janela vencida (> 2.4s) e a Nuvemshop voltou: reprocessa e vira pedido
    relogio.avancar(2.0)
    del client.falhas["consumo-backoff-1"]
    assert await _tick(db_session, client, backoff) == 1
    assert client.chamadas == ["consumo-backoff-1", "consumo-backoff-1"]
    assert await _status_evento(db_session, evento) == "PROCESSADO"
    assert await _total_pedidos(db_session, "consumo-backoff-1") == 1


# ── (iv) teto de tentativas -> CONFLITO_MANUAL sem chamar o processador ──
async def test_teto_de_tentativas_marca_conflito_manual_sem_reprocessar(
    db_session: AsyncSession, usuario_integracao: UsuarioModel
) -> None:
    evento = await _registrar_evento(db_session, id_recurso_externo="consumo-envenenado-1")
    await db_session.execute(
        text(
            "UPDATE webhook_evento SET status = 'ERRO', tentativas = :n, "
            "erro_detalhe = 'HTTP 503' WHERE id = :id"
        ),
        {"n": MAX_TENTATIVAS_WEBHOOK, "id": evento.id},
    )
    await db_session.commit()
    conflitos_antes = REGISTRY.get_sample_value("webhook_evento_conflito_manual_total") or 0.0
    client = _NuvemshopClientFake()

    tratados = await _tick(db_session, client, BackoffWebhookEmMemoria())

    assert tratados == 1
    assert client.chamadas == []
    assert await _status_evento(db_session, evento) == "CONFLITO_MANUAL"
    detalhe = await db_session.scalar(
        text("SELECT erro_detalhe FROM webhook_evento WHERE id = :id"), {"id": evento.id}
    )
    assert detalhe == "teto de 12 tentativas esgotado; último erro: HTTP 503"
    conflitos_depois = REGISTRY.get_sample_value("webhook_evento_conflito_manual_total") or 0.0
    assert conflitos_depois == conflitos_antes + 1


# ── (v) exceção inesperada (transação abortada) não impede o evento seguinte ──
async def test_excecao_inesperada_com_transacao_abortada_nao_impede_o_proximo_evento(
    db_session: AsyncSession, usuario_integracao: UsuarioModel, criar_variante_com_estoque
) -> None:
    await _mapear_variante(
        db_session, criar_variante_com_estoque, variante_externo_id="v-consumo-3"
    )
    envenenado = await _registrar_evento(db_session, id_recurso_externo="consumo-poison-1")
    bom = await _registrar_evento(db_session, id_recurso_externo="consumo-bom-1")
    client = _NuvemshopClientFake(
        {
            "consumo-bom-1": _pedido_dto(
                "consumo-bom-1", variante_externo_id="v-consumo-3", valor="49.90"
            )
        }
    )

    async def _aborta_transacao() -> None:
        # Erro de banco de verdade: deixa a transação em estado abortado —
        # sem o rollback do use case, o `marcar_erro` e o evento seguinte
        # falhariam com `InFailedSQLTransactionError`.
        await db_session.execute(text("SELECT 1/0"))

    client.ganchos["consumo-poison-1"] = _aborta_transacao

    tratados = await _tick(db_session, client, BackoffWebhookEmMemoria())

    assert tratados == 2
    assert await _status_evento(db_session, envenenado) == "ERRO"
    detalhe = await db_session.scalar(
        text("SELECT erro_detalhe FROM webhook_evento WHERE id = :id"), {"id": envenenado.id}
    )
    assert detalhe is not None and "erro inesperado" in detalhe
    assert await _status_evento(db_session, bom) == "PROCESSADO"
    assert await _total_pedidos(db_session, "consumo-bom-1") == 1


# ── contar_pendentes (gauge `integracao_outbox_pendente{fila="webhook"}`) ──
async def test_contar_pendentes_webhook_conta_pendente_e_erro_e_ignora_terminais(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyWebhookEventoRepository(db_session)
    antes = await repo.contar_pendentes()

    pendente = await _registrar_evento(db_session, id_recurso_externo="contar-pendente-1")
    com_erro = await _registrar_evento(db_session, id_recurso_externo="contar-erro-1")
    processado = await _registrar_evento(db_session, id_recurso_externo="contar-processado-1")
    conflito = await _registrar_evento(db_session, id_recurso_externo="contar-conflito-1")
    await repo.marcar_erro(com_erro.id, detalhe="x")
    await repo.marcar_processado(processado.id)
    await repo.marcar_conflito_manual(conflito.id, detalhe="y")
    await db_session.commit()

    assert pendente.id != com_erro.id
    assert await repo.contar_pendentes() == antes + 2  # PENDENTE + ERRO
