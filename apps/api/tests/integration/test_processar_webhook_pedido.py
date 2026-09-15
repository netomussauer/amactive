"""Teste de integração ponta a ponta de `ProcessarWebhookPedidoUseCase`
(Postgres real, `NuvemshopClientPort` mockado por injeção de dependência —
nunca uma chamada HTTP real) — ver docs/design-integracao-nuvemshop.md §5.3
e §9 item 6: "um pedido Nuvemshop de teste já deve conseguir virar um
Pedido CONFIRMADO no AMACTIVE, ponta a ponta".

Cobre os três desfechos do diagrama de sequência de design §5.3: sucesso
(pedido CONFIRMADO, cliente criado, estoque baixado), item sem
`MapeamentoVarianteCanal` (`CONFLITO_MANUAL`, tudo ou nada) e reprocessamento
do mesmo `pedido_externo_id` (`PedidoExternoJaProcessado`, idempotente — não
cria um segundo pedido nem duplica a baixa de estoque)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from prometheus_client import REGISTRY
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyEstoqueRepository,
)
from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel
from amactive.contexts.integracao_canais.application.use_cases.processar_webhook_pedido import (
    ProcessarWebhookPedidoUseCase,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao, WebhookEvento
from amactive.contexts.integracao_canais.domain.repositories import (
    EnderecoExterno,
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
    """O cache de processo do `usuario_id` de integração (design §3.1,
    `vendas_gateway.py`) precisa ser resetado entre testes: cada teste roda
    em uma transação própria (revertida no teardown — ver
    tests/integration/conftest.py) e um `usuario_id` cacheado por um teste
    anterior apontaria para uma linha que já não existe na transação de um
    teste seguinte, quebrando a FK de `pedido.usuario_id`."""
    resetar_cache_usuario_integracao_para_testes()
    yield
    resetar_cache_usuario_integracao_para_testes()


@pytest.fixture
async def usuario_integracao(db_session: AsyncSession) -> UsuarioModel:
    """Mesmo usuário seedado por `scripts/bootstrap_usuario_integracao.py`
    (design §3.1) — `ativo=False` (nunca loga), `papel=VENDEDOR`."""
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


class _NuvemshopClientFake:
    """Fake mínimo de `NuvemshopClientPort` — só `buscar_pedido` é exercido
    por `ProcessarWebhookPedidoUseCase` (design §5.3); os demais métodos do
    Protocol existem apenas para satisfazer a assinatura estrutural."""

    def __init__(self, pedido: NuvemshopPedidoDTO) -> None:
        self._pedido = pedido

    async def buscar_pedido(self, pedido_externo_id: str) -> NuvemshopPedidoDTO:
        assert pedido_externo_id == self._pedido.pedido_externo_id
        return self._pedido

    async def criar_produto(self, produto: ProdutoParaPublicacao) -> PublicacaoResultado:
        raise NotImplementedError("Não exercido por ProcessarWebhookPedidoUseCase.")

    async def atualizar_produto(
        self, produto_externo_id: str, produto: ProdutoParaPublicacao
    ) -> PublicacaoResultado:
        raise NotImplementedError("Não exercido por ProcessarWebhookPedidoUseCase.")

    async def atualizar_estoque_variante(
        self, *, produto_externo_id: str, variante_externo_id: str, quantidade: int
    ) -> None:
        raise NotImplementedError("Não exercido por ProcessarWebhookPedidoUseCase.")

    async def listar_pedidos_recentes(self, *, desde: datetime) -> list[str]:
        raise NotImplementedError("Não exercido por ProcessarWebhookPedidoUseCase.")


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


def _montar_use_case(
    db_session: AsyncSession,
    *,
    pedido_externo: NuvemshopPedidoDTO,
    mapeamento_repo: SqlAlchemyMapeamentoVarianteRepository,
    webhook_repo: SqlAlchemyWebhookEventoRepository,
) -> ProcessarWebhookPedidoUseCase:
    return ProcessarWebhookPedidoUseCase(
        nuvemshop_client=_NuvemshopClientFake(pedido_externo),
        cliente_integracao=CadastrosIntegracaoGateway(db_session),
        mapeamento_variante_repository=mapeamento_repo,
        pedido_integracao=VendasIntegracaoGateway(db_session),
        webhook_evento_repository=webhook_repo,
    )


async def test_pedido_nuvemshop_vira_pedido_confirmado_cliente_e_baixa_estoque(
    db_session: AsyncSession,
    usuario_integracao: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="99.90")

    mapeamento_repo = SqlAlchemyMapeamentoVarianteRepository(db_session)
    await mapeamento_repo.upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="111",
        variante_externo_id="222",
    )
    await db_session.commit()

    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    evento = await _registrar_evento(db_session, id_recurso_externo="555000111")

    pedido_externo = NuvemshopPedidoDTO(
        pedido_externo_id="555000111",
        cliente_email="cliente.nuvemshop@example.com",
        cliente_nome="Cliente Nuvemshop",
        cliente_cpf_cnpj="12345678900",
        cliente_telefone="11999990000",
        cliente_endereco=EnderecoExterno(
            logradouro="Rua das Flores, 10", cidade="São Paulo", uf="SP", cep="01000-000"
        ),
        cliente_externo_id="cliente-externo-1",
        itens=[
            ItemPedidoExternoDTO(variante_externo_id="222", produto_externo_id="111", quantidade=2)
        ],
        valor_total=Decimal("199.80"),
    )

    use_case = _montar_use_case(
        db_session,
        pedido_externo=pedido_externo,
        mapeamento_repo=mapeamento_repo,
        webhook_repo=webhook_repo,
    )
    await use_case.executar(evento)
    await db_session.commit()

    evento_status = await db_session.scalar(
        text("SELECT status FROM webhook_evento WHERE id = :id"), {"id": evento.id}
    )
    assert evento_status == "PROCESSADO"

    pedido_linha = (
        (
            await db_session.execute(
                text(
                    "SELECT status, origem_canal, valor_total FROM pedido "
                    "WHERE pedido_externo_id = '555000111' AND origem_canal = 'NUVEMSHOP'"
                )
            )
        )
        .mappings()
        .one()
    )
    assert pedido_linha["status"] == "CONFIRMADO"
    assert pedido_linha["origem_canal"] == "NUVEMSHOP"
    assert Decimal(pedido_linha["valor_total"]) == Decimal("199.80")

    cliente_linha = (
        (
            await db_session.execute(
                text(
                    "SELECT origem_cadastro, cliente_externo_id FROM cliente "
                    "WHERE email = 'cliente.nuvemshop@example.com'"
                )
            )
        )
        .mappings()
        .one()
    )
    assert cliente_linha["origem_cadastro"] == "NUVEMSHOP"
    assert cliente_linha["cliente_externo_id"] == "cliente-externo-1"

    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)
    assert estoque is not None
    assert estoque.quantidade == 8


async def test_valor_total_divergente_do_preco_amactive_marca_conflito_manual(
    db_session: AsyncSession,
    usuario_integracao: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    """`CriarPedidoUseCase` (Core Vendas, inalterado) exige que a soma dos
    pagamentos bata exatamente com o subtotal calculado a partir do
    `preco_venda` ATUAL do AMACTIVE. Um pedido Nuvemshop real diverge disso
    com frequência (frete incluso no total, cupom aplicado do lado da
    Nuvemshop, preço reajustado no AMACTIVE depois da última publicação de
    catálogo) — aqui simulado com `valor_total` incluindo algo além do
    preço da variante (200.00 vs. 2x99.90=199.80). Isso NUNCA pode crashar
    o worker sem tratamento: deve virar CONFLITO_MANUAL, mesma severidade
    de estoque insuficiente (pedido já pago, precisa de revisão humana),
    sem criar nenhum pedido."""
    variante = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="99.90")
    mapeamento_repo = SqlAlchemyMapeamentoVarianteRepository(db_session)
    await mapeamento_repo.upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="p-frete",
        variante_externo_id="v-frete",
    )
    await db_session.commit()

    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    evento = await _registrar_evento(db_session, id_recurso_externo="pedido-com-frete")

    pedido_externo = NuvemshopPedidoDTO(
        pedido_externo_id="pedido-com-frete",
        cliente_email="frete@example.com",
        cliente_nome="Cliente Com Frete",
        cliente_cpf_cnpj=None,
        cliente_telefone=None,
        cliente_endereco=None,
        cliente_externo_id="cliente-frete",
        itens=[
            ItemPedidoExternoDTO(
                variante_externo_id="v-frete", produto_externo_id="p-frete", quantidade=2
            )
        ],
        # 2 x 99.90 = 199.80 no AMACTIVE, mas a Nuvemshop informou 200.00
        # (ex.: frete incluso no total do pedido).
        valor_total=Decimal("200.00"),
    )

    use_case = _montar_use_case(
        db_session,
        pedido_externo=pedido_externo,
        mapeamento_repo=mapeamento_repo,
        webhook_repo=webhook_repo,
    )
    await use_case.executar(evento)
    await db_session.commit()

    evento_status = await db_session.scalar(
        text("SELECT status FROM webhook_evento WHERE id = :id"), {"id": evento.id}
    )
    assert evento_status == "CONFLITO_MANUAL"

    total_pedidos = await db_session.scalar(
        text("SELECT count(*) FROM pedido WHERE pedido_externo_id = 'pedido-com-frete'")
    )
    assert total_pedidos == 0

    # Estoque não deve ter sido baixado — a validação de pagamento falha
    # dentro de CriarPedidoUseCase antes de qualquer baixa (ver
    # criar_pedido.py: pagamentos são validados antes do loop de baixa de
    # estoque), então o rollback da transação garante isso.
    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)
    assert estoque is not None
    assert estoque.quantidade == 10


async def test_estoque_insuficiente_no_momento_do_processamento_marca_conflito_manual(
    db_session: AsyncSession,
    usuario_integracao: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    """Terceiro cenário exigido por design §9 passo 10 / avaliação §2.2: o
    saldo pode ter caído entre o momento da compra na Nuvemshop (já paga) e
    o momento em que o worker processa o webhook — ex.: uma venda no PDV ou
    outro pedido externo consumiu o estoque nesse intervalo. `EstoquePort`
    (via `fn_aplicar_movimentacao_estoque`, já existente) rejeita a baixa
    com `SaldoDeEstoqueInsuficiente`, e `CriarPedidoUseCase` propaga isso
    após já ter tentado a baixa de algum item — a transação inteira reverte
    (mesmo comportamento já validado para o PDV em
    tests/integration/test_criar_pedido.py). Aqui, confirma que o webhook
    trata isso como CONFLITO_MANUAL (pedido já pago, precisa de revisão
    humana) em vez de deixar a exceção subir sem tratamento."""
    variante = await criar_variante_com_estoque(quantidade_inicial=1, preco_venda="50.00")
    mapeamento_repo = SqlAlchemyMapeamentoVarianteRepository(db_session)
    await mapeamento_repo.upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="p-sem-saldo",
        variante_externo_id="v-sem-saldo",
    )
    await db_session.commit()

    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    evento = await _registrar_evento(db_session, id_recurso_externo="pedido-sem-saldo")

    pedido_externo = NuvemshopPedidoDTO(
        pedido_externo_id="pedido-sem-saldo",
        cliente_email="semsaldo@example.com",
        cliente_nome="Cliente Sem Saldo",
        cliente_cpf_cnpj=None,
        cliente_telefone=None,
        cliente_endereco=None,
        cliente_externo_id="cliente-sem-saldo",
        itens=[
            ItemPedidoExternoDTO(
                variante_externo_id="v-sem-saldo",
                produto_externo_id="p-sem-saldo",
                # Só há 1 unidade em estoque — pedido pede 5.
                quantidade=5,
            )
        ],
        valor_total=Decimal("250.00"),
    )

    antes_metrica_conflito = (
        REGISTRY.get_sample_value("webhook_evento_conflito_manual_total") or 0.0
    )

    use_case = _montar_use_case(
        db_session,
        pedido_externo=pedido_externo,
        mapeamento_repo=mapeamento_repo,
        webhook_repo=webhook_repo,
    )
    await use_case.executar(evento)
    await db_session.commit()

    evento_status = await db_session.scalar(
        text("SELECT status FROM webhook_evento WHERE id = :id"), {"id": evento.id}
    )
    assert evento_status == "CONFLITO_MANUAL"

    # Métrica `webhook_evento_conflito_manual_total` (design §5.4/§8) —
    # incrementada dentro de
    # `SqlAlchemyWebhookEventoRepository.marcar_conflito_manual` — este é o
    # cenário de maior severidade de negócio (design §8/item 6:
    # `SaldoDeEstoqueInsuficiente` também gera um log ERROR dedicado).
    depois_metrica_conflito = REGISTRY.get_sample_value("webhook_evento_conflito_manual_total")
    assert depois_metrica_conflito == antes_metrica_conflito + 1

    total_pedidos = await db_session.scalar(
        text("SELECT count(*) FROM pedido WHERE pedido_externo_id = 'pedido-sem-saldo'")
    )
    assert total_pedidos == 0

    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)
    assert estoque is not None
    assert estoque.quantidade == 1  # Rollback atômico — não foi debitado


async def test_item_sem_mapeamento_marca_conflito_manual_sem_criar_pedido_parcial(
    db_session: AsyncSession,
) -> None:
    evento = await _registrar_evento(db_session, id_recurso_externo="900")
    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    mapeamento_repo = SqlAlchemyMapeamentoVarianteRepository(db_session)

    pedido_externo = NuvemshopPedidoDTO(
        pedido_externo_id="900",
        cliente_email="sem.mapeamento@example.com",
        cliente_nome="Cliente Sem Mapeamento",
        cliente_cpf_cnpj=None,
        cliente_telefone=None,
        cliente_endereco=None,
        cliente_externo_id="cliente-sem-mapeamento",
        itens=[
            ItemPedidoExternoDTO(
                variante_externo_id="variante-nunca-mapeada",
                produto_externo_id="produto-nunca-mapeado",
                quantidade=1,
            )
        ],
        valor_total=Decimal("50.00"),
    )

    use_case = _montar_use_case(
        db_session,
        pedido_externo=pedido_externo,
        mapeamento_repo=mapeamento_repo,
        webhook_repo=webhook_repo,
    )
    await use_case.executar(evento)
    await db_session.commit()

    evento_status = await db_session.scalar(
        text("SELECT status FROM webhook_evento WHERE id = :id"), {"id": evento.id}
    )
    assert evento_status == "CONFLITO_MANUAL"

    total_pedidos = await db_session.scalar(
        text("SELECT count(*) FROM pedido WHERE pedido_externo_id = '900'")
    )
    assert total_pedidos == 0


async def test_reprocessar_mesmo_pedido_externo_e_idempotente_nao_duplica(
    db_session: AsyncSession,
    usuario_integracao: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="99.90")
    mapeamento_repo = SqlAlchemyMapeamentoVarianteRepository(db_session)
    await mapeamento_repo.upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="p1",
        variante_externo_id="v1",
    )
    await db_session.commit()

    webhook_repo = SqlAlchemyWebhookEventoRepository(db_session)
    # Dois eventos distintos (ex.: webhook + reconciliação concorrentes,
    # design §3.5/§5.2) referenciando o MESMO id_recurso_externo (o "id" do
    # pedido na Nuvemshop, usado em `GET /orders/{id}` — ver design §5.3
    # passo 1) — `tipo_evento` diferente evita colisão na UNIQUE de
    # `evento_externo_id` (design §2.4), simulando webhook + reconciliação.
    evento_1 = await _registrar_evento(
        db_session, id_recurso_externo="pedido-duplicado-1", tipo_evento="order/paid"
    )
    evento_2 = await _registrar_evento(
        db_session, id_recurso_externo="pedido-duplicado-1", tipo_evento="reconciliacao"
    )

    pedido_externo = NuvemshopPedidoDTO(
        pedido_externo_id="pedido-duplicado-1",
        cliente_email="duplicado@example.com",
        cliente_nome="Cliente Duplicado",
        cliente_cpf_cnpj=None,
        cliente_telefone=None,
        cliente_endereco=None,
        cliente_externo_id="cliente-duplicado",
        itens=[
            ItemPedidoExternoDTO(variante_externo_id="v1", produto_externo_id="p1", quantidade=1)
        ],
        valor_total=Decimal("99.90"),
    )

    await _montar_use_case(
        db_session,
        pedido_externo=pedido_externo,
        mapeamento_repo=mapeamento_repo,
        webhook_repo=webhook_repo,
    ).executar(evento_1)
    await db_session.commit()

    await _montar_use_case(
        db_session,
        pedido_externo=pedido_externo,
        mapeamento_repo=mapeamento_repo,
        webhook_repo=webhook_repo,
    ).executar(evento_2)
    await db_session.commit()

    status_1 = await db_session.scalar(
        text("SELECT status FROM webhook_evento WHERE id = :id"), {"id": evento_1.id}
    )
    status_2 = await db_session.scalar(
        text("SELECT status FROM webhook_evento WHERE id = :id"), {"id": evento_2.id}
    )
    assert status_1 == "PROCESSADO"
    # Idempotente: o segundo evento também termina como PROCESSADO (não é
    # erro) mesmo sem ter criado um novo pedido — design §5.3/§5.2.
    assert status_2 == "PROCESSADO"

    total_pedidos = await db_session.scalar(
        text("SELECT count(*) FROM pedido WHERE pedido_externo_id = 'pedido-duplicado-1'")
    )
    assert total_pedidos == 1

    # Estoque baixado uma única vez (2ª tentativa nunca chegou a registrar
    # saída — a violação de UNIQUE acontece antes, ver vendas_gateway.py).
    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)
    assert estoque is not None
    assert estoque.quantidade == 9
