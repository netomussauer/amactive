"""Teste de integração ponta a ponta de `PublicarEstoqueCanalUseCase`
(Postgres real, `NuvemshopClientPort` fake — nunca uma chamada HTTP real) —
ver docs/design-integracao-nuvemshop.md §4 e §9 item 7: "validar que uma
venda no PDV propaga o saldo pra Nuvemshop dentro de segundos".

Cobre:
- o objetivo central do passo 7: uma venda via `CriarPedidoUseCase` baixa o
  estoque, o trigger de banco (`fn_enfileirar_outbox_estoque`, já existente
  desde a migration 000005) enfileira `integracao_estoque_outbox`, e
  `PublicarEstoqueCanalUseCase` publica o saldo absoluto atual via
  `NuvemshopClientPort.atualizar_estoque_variante` com os IDs/quantidade
  corretos, marcando a linha como `ENVIADO`;
- coalescing (design §4.2): múltiplas mudanças rápidas na mesma variante
  geram múltiplas linhas de outbox, mas só uma chamada HTTP é feita (o
  saldo absoluto mais recente) e TODAS as linhas (inclusive as
  "supersededas") terminam `ENVIADO`;
- retry com backoff exponencial + jitter em falha transitória (5xx),
  falha definitiva sem retry em 4xx (exceto 429), e o teto de tentativas
  (design §4.3);
- a decisão documentada de marcar `ENVIADO` sem chamar o client quando não
  há `MapeamentoVarianteCanal` ainda (nada a publicar)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.domain.entities import MotivoMovimentacao, TipoMovimentacao
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyMovimentacaoRepository,
)
from amactive.contexts.integracao_canais.application.use_cases.publicar_estoque_canal import (
    PublicarEstoqueCanalUseCase,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao
from amactive.contexts.integracao_canais.domain.exceptions import NuvemshopIndisponivel
from amactive.contexts.integracao_canais.domain.repositories import (
    NuvemshopPedidoDTO,
    ProdutoParaPublicacao,
    PublicacaoResultado,
)
from amactive.contexts.integracao_canais.infrastructure.persistence.repositories import (
    SqlAlchemyIntegracaoEstoqueOutboxRepository,
    SqlAlchemyMapeamentoVarianteRepository,
)
from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.application.use_cases.criar_pedido import CriarPedidoUseCase
from amactive.contexts.vendas.domain.entities import FormaPagamento
from amactive.contexts.vendas.infrastructure.persistence.gateways import CatalogoEstoqueGateway
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
)

pytestmark = pytest.mark.integration

# Grande o suficiente para cobrir qualquer outra linha PENDENTE/ERRO
# pré-existente na tabela no momento do teste — `db_session` isola CADA
# teste em uma transação própria (savepoint revertido no teardown, ver
# tests/integration/conftest.py), mas pelo menos um outro teste do
# repositório (`test_api_fluxo_completo.py`) sobrescreve deliberadamente
# `get_db_session` com uma sessão ligada direto ao `test_engine` (sem essa
# transação externa) para exercitar o fluxo HTTP completo — o que deixa
# produto/variante/estoque REAIS committados no banco de teste entre
# execuções, o que por sua vez populam `integracao_estoque_outbox` de
# verdade via trigger. Os testes abaixo nunca dependem de serem os únicos
# dados na fila: usam um `limite` folgado para garantir que a PRÓPRIA linha
# entra no lote processado, e só afirmam sobre `client.chamadas` (que só
# recebe entradas de variantes com `MapeamentoVarianteCanal` — nenhuma
# variante de outro teste tem mapeamento) e sobre as linhas da PRÓPRIA
# variante (consultas sempre filtradas por `variante_id`).
_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS = 100_000


class _NuvemshopClientEstoqueFake:
    """Fake mínimo de `NuvemshopClientPort` — só `atualizar_estoque_variante`
    é exercido por `PublicarEstoqueCanalUseCase`; os demais métodos do
    Protocol existem apenas para satisfazer a assinatura estrutural.

    `excecoes_por_chamada`: uma exceção a levantar na N-ésima chamada
    (1-indexada); chamadas além do fim da lista têm sucesso. Permite
    simular "falha na 1ª tentativa, sucesso na 2ª" sem duplicar fakes."""

    def __init__(self, *, excecoes_por_chamada: list[Exception | None] | None = None) -> None:
        self.chamadas: list[tuple[str, str, int]] = []
        self._excecoes = excecoes_por_chamada or []

    async def buscar_pedido(self, pedido_externo_id: str) -> NuvemshopPedidoDTO:
        raise NotImplementedError("Não exercido por PublicarEstoqueCanalUseCase.")

    async def criar_produto(self, produto: ProdutoParaPublicacao) -> PublicacaoResultado:
        raise NotImplementedError("Não exercido por PublicarEstoqueCanalUseCase.")

    async def atualizar_produto(
        self, produto_externo_id: str, produto: ProdutoParaPublicacao
    ) -> PublicacaoResultado:
        raise NotImplementedError("Não exercido por PublicarEstoqueCanalUseCase.")

    async def atualizar_estoque_variante(
        self, *, produto_externo_id: str, variante_externo_id: str, quantidade: int
    ) -> None:
        indice = len(self.chamadas)
        self.chamadas.append((produto_externo_id, variante_externo_id, quantidade))
        if indice < len(self._excecoes) and self._excecoes[indice] is not None:
            raise self._excecoes[indice]  # type: ignore[misc]


def _use_case(
    db_session: AsyncSession, client: _NuvemshopClientEstoqueFake
) -> PublicarEstoqueCanalUseCase:
    return PublicarEstoqueCanalUseCase(
        nuvemshop_client=client,
        mapeamento_variante_repository=SqlAlchemyMapeamentoVarianteRepository(db_session),
        outbox_repository=SqlAlchemyIntegracaoEstoqueOutboxRepository(db_session),
    )


async def _status_outbox_da_variante(
    db_session: AsyncSession, variante_id: UUID
) -> list[dict[str, object]]:
    resultado = await db_session.execute(
        text(
            "SELECT id, status, quantidade_publicada, tentativas, proxima_tentativa_em "
            "FROM integracao_estoque_outbox WHERE variante_id = :variante_id "
            "ORDER BY criado_em"
        ),
        {"variante_id": variante_id},
    )
    return [dict(linha) for linha in resultado.mappings().all()]


async def _empurrar_criado_em_das_linhas_novas(
    db_session: AsyncSession, *, variante_id: UUID, ids_ja_vistos: set[UUID], segundos: float
) -> set[UUID]:
    """Só para setup determinístico de teste — NUNCA usado pela aplicação.

    O Postgres congela `now()` no INÍCIO da transação (não por statement) —
    então múltiplas linhas de outbox criadas pelo trigger dentro do MESMO
    teste (via `db_session`, isolado por SAVEPOINT dentro de uma única
    transação real — ver `join_transaction_mode="create_savepoint"` em
    tests/integration/conftest.py) acabam todas com o MESMO `criado_em`,
    tornando "a mais recente" ambíguo. Isso NUNCA acontece em produção
    (cada venda é uma transação própria, com seu próprio `now()` — a
    query de coalescing de design §4.2 depende exatamente dessa garantia).

    Esta função identifica a(s) linha(s) de outbox da variante que ainda
    não tinham sido vistas na chamada anterior (ou seja, a que o trigger
    acabou de criar) e empurra só o `criado_em` DELAS para
    `now() + segundos` — restaura a ordenação temporal real que existiria
    em produção, sem fabricar nenhum dado de negócio (`quantidade_publicada`
    continua exatamente o que o trigger calculou)."""
    resultado = await db_session.execute(
        text("SELECT id FROM integracao_estoque_outbox WHERE variante_id = :variante_id"),
        {"variante_id": variante_id},
    )
    todos_ids = {linha[0] for linha in resultado.all()}
    novos_ids = todos_ids - ids_ja_vistos
    if novos_ids:
        await db_session.execute(
            text(
                "UPDATE integracao_estoque_outbox "
                "SET criado_em = now() + make_interval(secs => :segundos) "
                "WHERE id = ANY(:ids)"
            ),
            {"segundos": segundos, "ids": list(novos_ids)},
        )
    return todos_ids


async def test_venda_pdv_propaga_saldo_para_nuvemshop_via_outbox(
    db_session: AsyncSession, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="100.00")
    await SqlAlchemyMapeamentoVarianteRepository(db_session).upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="produto-111",
        variante_externo_id="variante-222",
    )
    await db_session.commit()
    # Ver docstring de `_empurrar_criado_em_das_linhas_novas` — restaura a
    # ordenação temporal real entre a linha de criação e a linha da venda
    # abaixo, que dentro desta única transação de teste teriam o mesmo
    # `criado_em`.
    ids_vistos = await _empurrar_criado_em_das_linhas_novas(
        db_session, variante_id=variante.id, ids_ja_vistos=set(), segundos=1
    )

    # Venda real via PDV — mesmo caminho de produção (trigger de estoque já
    # populou 1 linha de outbox na criação da variante acima, com
    # quantidade_publicada=10; esta venda gera uma 2ª linha com
    # quantidade_publicada=7).
    gateway = CatalogoEstoqueGateway(db_session)
    pedido = await CriarPedidoUseCase(
        SqlAlchemyPedidoRepository(db_session), gateway, gateway
    ).executar(
        cliente_id=None,
        desconto=Decimal("0.00"),
        observacao=None,
        itens=[
            ItemPedidoInput(variante_id=variante.id, quantidade=3, desconto_item=Decimal("0.00"))
        ],
        pagamentos=[PagamentoInput(forma_pagamento=FormaPagamento.PIX, valor=Decimal("300.00"))],
        usuario_id=usuario_teste.id,
    )
    await db_session.commit()
    assert pedido.valor_total == Decimal("300.00")
    await _empurrar_criado_em_das_linhas_novas(
        db_session, variante_id=variante.id, ids_ja_vistos=ids_vistos, segundos=2
    )

    linhas_antes = await _status_outbox_da_variante(db_session, variante.id)
    assert len(linhas_antes) == 2
    assert all(linha["status"] == "PENDENTE" for linha in linhas_antes)

    client = _NuvemshopClientEstoqueFake()
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    # Coalescing: 2 linhas de outbox para a mesma variante, mas só 1 chamada
    # HTTP — com o saldo ABSOLUTO mais recente (7, não um delta de -3).
    assert processados >= 1  # >= pois pode incluir linhas pre-existentes de outros testes
    assert client.chamadas == [("produto-111", "variante-222", 7)]

    linhas_depois = await _status_outbox_da_variante(db_session, variante.id)
    assert len(linhas_depois) == 2
    assert all(linha["status"] == "ENVIADO" for linha in linhas_depois)


async def test_coalescing_tres_mudancas_rapidas_geram_uma_unica_chamada_http(
    db_session: AsyncSession, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=20, preco_venda="10.00")
    await SqlAlchemyMapeamentoVarianteRepository(db_session).upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="p-rapido",
        variante_externo_id="v-rapido",
    )
    await db_session.commit()
    # Ver docstring de `_empurrar_criado_em_das_linhas_novas`.
    ids_vistos = await _empurrar_criado_em_das_linhas_novas(
        db_session, variante_id=variante.id, ids_ja_vistos=set(), segundos=1
    )

    mov_repo = SqlAlchemyMovimentacaoRepository(db_session)
    for indice in range(2):
        await mov_repo.registrar(
            variante_id=variante.id,
            tipo=TipoMovimentacao.SAIDA,
            quantidade=1,
            motivo=MotivoMovimentacao.PERDA,
            usuario_id=usuario_teste.id,
        )
        await db_session.commit()
        ids_vistos = await _empurrar_criado_em_das_linhas_novas(
            db_session, variante_id=variante.id, ids_ja_vistos=ids_vistos, segundos=2 + indice
        )

    # 1 linha da criação inicial (quantidade_inicial=20) + 2 das saídas
    # rápidas acima = 3 linhas PENDENTE para a mesma variante.
    linhas_antes = await _status_outbox_da_variante(db_session, variante.id)
    assert len(linhas_antes) == 3

    client = _NuvemshopClientEstoqueFake()
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1  # >= pois pode incluir linhas pre-existentes de outros testes
    assert client.chamadas == [("p-rapido", "v-rapido", 18)]

    linhas_depois = await _status_outbox_da_variante(db_session, variante.id)
    assert len(linhas_depois) == 3
    assert all(linha["status"] == "ENVIADO" for linha in linhas_depois)


async def test_item_sem_mapeamento_marca_enviado_sem_chamar_client(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    await db_session.commit()

    client = _NuvemshopClientEstoqueFake()
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1  # >= pois pode incluir linhas pre-existentes de outros testes
    assert client.chamadas == []  # nada a publicar — variante nunca mapeada

    linhas = await _status_outbox_da_variante(db_session, variante.id)
    assert len(linhas) == 1
    assert linhas[0]["status"] == "ENVIADO"


async def test_falha_5xx_agenda_retry_com_backoff_e_jitter(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    await SqlAlchemyMapeamentoVarianteRepository(db_session).upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="p-erro",
        variante_externo_id="v-erro",
    )
    await db_session.commit()

    client = _NuvemshopClientEstoqueFake(
        excecoes_por_chamada=[
            NuvemshopIndisponivel("Erro transitório da Nuvemshop.", status_code_origem=500)
        ]
    )
    antes = datetime.now(UTC)
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1  # >= pois pode incluir linhas pre-existentes de outros testes
    assert len(client.chamadas) == 1

    linhas = await _status_outbox_da_variante(db_session, variante.id)
    assert len(linhas) == 1
    assert linhas[0]["status"] == "ERRO"
    assert linhas[0]["tentativas"] == 1
    proxima_tentativa_em = linhas[0]["proxima_tentativa_em"]
    assert proxima_tentativa_em is not None
    # tentativa 1 -> 2s base, ±20% de jitter (design §4.3): entre 1.6s e
    # 2.4s de atraso a partir de "antes" — folga generosa para não deixar o
    # teste flaky por tempo de execução do próprio teste.
    atraso = (proxima_tentativa_em - antes).total_seconds()
    assert 1.0 < atraso < 10.0


async def test_falha_4xx_nao_e_retentada_automaticamente(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    await SqlAlchemyMapeamentoVarianteRepository(db_session).upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="p-4xx",
        variante_externo_id="v-4xx",
    )
    await db_session.commit()

    client = _NuvemshopClientEstoqueFake(
        excecoes_por_chamada=[NuvemshopIndisponivel("Payload malformado.", status_code_origem=400)]
    )
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1  # >= pois pode incluir linhas pre-existentes de outros testes
    linhas = await _status_outbox_da_variante(db_session, variante.id)
    assert linhas[0]["status"] == "ERRO"
    assert linhas[0]["tentativas"] == 1
    # 4xx (exceto 429) nunca é retentado automaticamente (design §4.3, mesmo
    # princípio de docs/SDD.md §5.2) — a linha some da fila ativa até
    # intervenção manual: `proxima_tentativa_em` é empurrada bem além de
    # qualquer janela de retry legítima (>1 ano à frente).
    proxima_tentativa_em = linhas[0]["proxima_tentativa_em"]
    assert (proxima_tentativa_em - datetime.now(UTC)).days > 365


async def test_teto_de_tentativas_esgotado_para_de_retentar(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    await SqlAlchemyMapeamentoVarianteRepository(db_session).upsert(
        variante_id=variante.id,
        canal=CanalIntegracao.NUVEMSHOP,
        produto_externo_id="p-teto",
        variante_externo_id="v-teto",
    )
    await db_session.commit()

    # Simula que a linha já falhou 7 vezes antes (setup direto via SQL —
    # equivalente a 7 ticks anteriores do worker já terem chamado
    # `marcar_erro_com_retry`, sem precisar rodar o use case 7 vezes de
    # verdade neste teste).
    await db_session.execute(
        text(
            "UPDATE integracao_estoque_outbox SET status = 'ERRO', tentativas = 7, "
            "proxima_tentativa_em = now() - interval '1 second' "
            "WHERE variante_id = :variante_id"
        ),
        {"variante_id": variante.id},
    )
    await db_session.commit()

    client = _NuvemshopClientEstoqueFake(
        excecoes_por_chamada=[NuvemshopIndisponivel("Ainda fora do ar.", status_code_origem=503)]
    )
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1  # >= pois pode incluir linhas pre-existentes de outros testes
    linhas = await _status_outbox_da_variante(db_session, variante.id)
    assert linhas[0]["status"] == "ERRO"
    # 8ª tentativa (7 + 1 desta chamada) atinge o teto `_MAX_TENTATIVAS_OUTBOX
    # = 8` (design §4.3) — falha definitiva, mesmo efeito de um 4xx.
    assert linhas[0]["tentativas"] == 8
    proxima_tentativa_em = linhas[0]["proxima_tentativa_em"]
    assert (proxima_tentativa_em - datetime.now(UTC)).days > 365
