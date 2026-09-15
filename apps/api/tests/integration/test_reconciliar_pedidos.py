"""Teste de integração de `ReconciliarPedidosUseCase` (Postgres real,
`NuvemshopClientPort` mockado por injeção de dependência — nunca uma chamada
HTTP real) — ver docs/design-integracao-nuvemshop.md §5.5 e §9 passo 12.

Cobre exatamente os três cenários exigidos pela tarefa: (a) um pedido
"perdido" (nunca chegou via webhook) é descoberto pela reconciliação e vira
um `Pedido CONFIRMADO`, exatamente como um webhook normal faria; (b) um
pedido que já tem QUALQUER `webhook_evento` (mesmo já `PROCESSADO`) não gera
um evento de reconciliação duplicado nem é reprocessado; (c) a reconciliação
usa `ProcessarWebhookPedidoUseCase` sem nenhuma lógica de negócio duplicada
— verificado indiretamente, por comportamento observável (um item sem
`MapeamentoVarianteCanal` produz o mesmo `CONFLITO_MANUAL` que o caminho de
webhook normal já produz, ver `test_processar_webhook_pedido.py`)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel
from amactive.contexts.integracao_canais.application.use_cases.processar_webhook_pedido import (
    ProcessarWebhookPedidoUseCase,
)
from amactive.contexts.integracao_canais.application.use_cases.reconciliar_pedidos import (
    JANELA_RETROSPECCAO,
    ReconciliarPedidosUseCase,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao
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
    """Ver mesma justificativa em `test_processar_webhook_pedido.py` — o
    cache de processo do `usuario_id` de integração precisa ser resetado
    entre testes."""
    resetar_cache_usuario_integracao_para_testes()
    yield
    resetar_cache_usuario_integracao_para_testes()


@pytest.fixture
async def usuario_integracao(db_session: AsyncSession) -> UsuarioModel:
    """Mesmo usuário seedado por `scripts/bootstrap_usuario_integracao.py`
    (design §3.1)."""
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


class _NuvemshopClientReconciliacaoFake:
    """Fake mínimo de `NuvemshopClientPort` — só `listar_pedidos_recentes`/
    `buscar_pedido` são exercidos por `ReconciliarPedidosUseCase` (via
    `ProcessarWebhookPedidoUseCase`); os demais métodos do Protocol existem
    apenas para satisfazer a assinatura estrutural.

    `pedidos_por_id` deliberadamente não precisa conter todo `ids_recentes`
    — um teste que espera que `buscar_pedido` NUNCA seja chamado (cenário
    "já conhecido", que deve ser pulado antes de qualquer chamada de rede)
    passa um dict vazio; `buscar_pedido` levanta `AssertionError` claro
    nesse caso, em vez de um `KeyError` genérico."""

    def __init__(
        self, *, ids_recentes: list[str], pedidos_por_id: dict[str, NuvemshopPedidoDTO]
    ) -> None:
        self._ids_recentes = ids_recentes
        self._pedidos_por_id = pedidos_por_id
        self.chamadas_listar_desde: list[datetime] = []
        self.chamadas_buscar_pedido: list[str] = []

    async def listar_pedidos_recentes(self, *, desde: datetime) -> list[str]:
        self.chamadas_listar_desde.append(desde)
        return list(self._ids_recentes)

    async def buscar_pedido(self, pedido_externo_id: str) -> NuvemshopPedidoDTO:
        self.chamadas_buscar_pedido.append(pedido_externo_id)
        if pedido_externo_id not in self._pedidos_por_id:
            raise AssertionError(
                f"buscar_pedido('{pedido_externo_id}') não deveria ter sido chamado neste teste "
                "(pedido já conhecido deveria ter sido pulado antes de qualquer chamada de rede)."
            )
        return self._pedidos_por_id[pedido_externo_id]

    async def criar_produto(self, produto: ProdutoParaPublicacao) -> PublicacaoResultado:
        raise NotImplementedError("Não exercido por ReconciliarPedidosUseCase.")

    async def atualizar_produto(
        self, produto_externo_id: str, produto: ProdutoParaPublicacao
    ) -> PublicacaoResultado:
        raise NotImplementedError("Não exercido por ReconciliarPedidosUseCase.")

    async def atualizar_estoque_variante(
        self, *, produto_externo_id: str, variante_externo_id: str, quantidade: int
    ) -> None:
        raise NotImplementedError("Não exercido por ReconciliarPedidosUseCase.")


def _montar_reconciliar_use_case(
    db_session: AsyncSession,
    *,
    client: _NuvemshopClientReconciliacaoFake,
    webhook_repo: SqlAlchemyWebhookEventoRepository,
) -> ReconciliarPedidosUseCase:
    processar_webhook_pedido = ProcessarWebhookPedidoUseCase(
        nuvemshop_client=client,
        cliente_integracao=CadastrosIntegracaoGateway(db_session),
        mapeamento_variante_repository=SqlAlchemyMapeamentoVarianteRepository(db_session),
        pedido_integracao=VendasIntegracaoGateway(db_session),
        webhook_evento_repository=webhook_repo,
    )
    return ReconciliarPedidosUseCase(
        nuvemshop_client=client,
        webhook_evento_repository=webhook_repo,
        processar_webhook_pedido=processar_webhook_pedido,
    )


# ── (a) pedido perdido descoberto pela reconciliação vira Pedido CONFIRMADO ──
async def test_pedido_perdido_e_descoberto_pela_reconciliacao_vira_pedido_confirmado(
    db_session: AsyncSession,
    usuario_integracao: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5, preco_venda="49.90")
    mapeamento_repo = SqlAlchemyMapeamentoVarianteRepository(db_session)
    await mapeamento_repo.upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="p-recon",
        variante_externo_id="v-recon",
    )
    await db_session.commit()

    pedido_externo = NuvemshopPedidoDTO(
        pedido_externo_id="pedido-perdido-1",
        cliente_email="perdido@example.com",
        cliente_nome="Cliente Perdido",
        cliente_cpf_cnpj=None,
        cliente_telefone=None,
        cliente_endereco=None,
        cliente_externo_id="cliente-perdido",
        itens=[
            ItemPedidoExternoDTO(
                variante_externo_id="v-recon", produto_externo_id="p-recon", quantidade=1
            )
        ],
        valor_total=Decimal("49.90"),
    )
    client = _NuvemshopClientReconciliacaoFake(
        ids_recentes=["pedido-perdido-1"],
        pedidos_por_id={"pedido-perdido-1": pedido_externo},
    )
    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    use_case = _montar_reconciliar_use_case(db_session, client=client, webhook_repo=webhook_repo)

    descobertos = await use_case.executar(confirmar_apos_cada_pedido=db_session.commit)

    assert descobertos == 1
    assert client.chamadas_buscar_pedido == ["pedido-perdido-1"]

    pedido_linha = (
        (
            await db_session.execute(
                text(
                    "SELECT status, origem_canal FROM pedido "
                    "WHERE pedido_externo_id = 'pedido-perdido-1' AND origem_canal = 'NUVEMSHOP'"
                )
            )
        )
        .mappings()
        .one()
    )
    assert pedido_linha["status"] == "CONFIRMADO"
    assert pedido_linha["origem_canal"] == "NUVEMSHOP"

    evento_linha = (
        (
            await db_session.execute(
                text(
                    "SELECT tipo_evento, status FROM webhook_evento "
                    "WHERE id_recurso_externo = 'pedido-perdido-1'"
                )
            )
        )
        .mappings()
        .one()
    )
    assert evento_linha["tipo_evento"] == "reconciliacao"
    assert evento_linha["status"] == "PROCESSADO"


# ── (b) pedido já conhecido não gera evento duplicado nem é reprocessado ──
async def test_pedido_ja_conhecido_via_webhook_nao_gera_evento_duplicado_nem_reprocessa(
    db_session: AsyncSession,
) -> None:
    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    # Simula um webhook normal que já tratou esse pedido — já PROCESSADO,
    # o caso mais exigente ("qualquer status, incluindo já PROCESSADO",
    # conforme a tarefa).
    evento_original = await webhook_repo.registrar_se_novo(
        canal=CanalIntegracao.NUVEMSHOP,
        tipo_evento="order/paid",
        id_recurso_externo="pedido-ja-conhecido-1",
        payload_bruto={"id": "pedido-ja-conhecido-1", "event": "order/paid"},
    )
    assert evento_original is not None
    await webhook_repo.marcar_processado(evento_original.id)
    await db_session.commit()

    # `pedidos_por_id` vazio de propósito — `buscar_pedido` nunca deveria
    # ser chamado para um pedido já conhecido (a checagem de
    # `existe_evento_para_recurso` precisa pular ANTES de qualquer chamada
    # de rede).
    client = _NuvemshopClientReconciliacaoFake(
        ids_recentes=["pedido-ja-conhecido-1"], pedidos_por_id={}
    )
    use_case = _montar_reconciliar_use_case(db_session, client=client, webhook_repo=webhook_repo)

    descobertos = await use_case.executar(confirmar_apos_cada_pedido=db_session.commit)

    assert descobertos == 0
    assert client.chamadas_buscar_pedido == []

    total_eventos = await db_session.scalar(
        text(
            "SELECT count(*) FROM webhook_evento WHERE id_recurso_externo = 'pedido-ja-conhecido-1'"
        )
    )
    assert total_eventos == 1  # nenhum evento de reconciliação novo criado

    status_evento = await db_session.scalar(
        text("SELECT status FROM webhook_evento WHERE id_recurso_externo = 'pedido-ja-conhecido-1'")
    )
    assert status_evento == "PROCESSADO"  # inalterado — nunca reprocessado

    total_pedidos = await db_session.scalar(
        text("SELECT count(*) FROM pedido WHERE pedido_externo_id = 'pedido-ja-conhecido-1'")
    )
    assert total_pedidos == 0  # nenhum Pedido criado por este teste


# ── (c) reconciliação reaproveita ProcessarWebhookPedidoUseCase, sem lógica
#     duplicada — verificado por comportamento observável: o mesmo desfecho
#     (CONFLITO_MANUAL, sem pedido criado) de um item sem
#     MapeamentoVarianteCanal, já coberto para o caminho de webhook normal em
#     test_processar_webhook_pedido.py. ──
async def test_reconciliacao_reaproveita_processar_webhook_pedido_use_case_sem_logica_duplicada(
    db_session: AsyncSession,
) -> None:
    pedido_externo = NuvemshopPedidoDTO(
        pedido_externo_id="pedido-recon-sem-mapeamento",
        cliente_email="semmap@example.com",
        cliente_nome="Cliente Sem Mapeamento",
        cliente_cpf_cnpj=None,
        cliente_telefone=None,
        cliente_endereco=None,
        cliente_externo_id="cliente-sem-mapeamento-recon",
        itens=[
            ItemPedidoExternoDTO(
                variante_externo_id="nunca-mapeada",
                produto_externo_id="nunca-mapeado",
                quantidade=1,
            )
        ],
        valor_total=Decimal("10.00"),
    )
    client = _NuvemshopClientReconciliacaoFake(
        ids_recentes=["pedido-recon-sem-mapeamento"],
        pedidos_por_id={"pedido-recon-sem-mapeamento": pedido_externo},
    )
    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    use_case = _montar_reconciliar_use_case(db_session, client=client, webhook_repo=webhook_repo)

    descobertos = await use_case.executar(confirmar_apos_cada_pedido=db_session.commit)

    assert descobertos == 1
    status_evento = await db_session.scalar(
        text(
            "SELECT status FROM webhook_evento "
            "WHERE id_recurso_externo = 'pedido-recon-sem-mapeamento'"
        )
    )
    assert status_evento == "CONFLITO_MANUAL"

    total_pedidos = await db_session.scalar(
        text("SELECT count(*) FROM pedido WHERE pedido_externo_id = 'pedido-recon-sem-mapeamento'")
    )
    assert total_pedidos == 0


# ── `desde` default usa a janela de retrospecção documentada ──
async def test_desde_padrao_usa_janela_de_retrospeccao_quando_nao_informado(
    db_session: AsyncSession,
) -> None:
    client = _NuvemshopClientReconciliacaoFake(ids_recentes=[], pedidos_por_id={})
    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    use_case = _montar_reconciliar_use_case(db_session, client=client, webhook_repo=webhook_repo)

    antes_da_chamada = datetime.now(UTC) - JANELA_RETROSPECCAO
    descobertos = await use_case.executar()
    depois_da_chamada = datetime.now(UTC) - JANELA_RETROSPECCAO

    assert descobertos == 0
    assert len(client.chamadas_listar_desde) == 1
    assert antes_da_chamada <= client.chamadas_listar_desde[0] <= depois_da_chamada
