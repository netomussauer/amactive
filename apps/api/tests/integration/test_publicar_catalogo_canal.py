"""Teste de integração ponta a ponta de `PublicarCatalogoCanalUseCase`
(Postgres real, `NuvemshopClientPort` fake — nunca uma chamada HTTP real) —
ver docs/design-integracao-nuvemshop.md §4 e §9 item 8: "validar criação e
atualização de produto".

Cobre:
- primeira publicação de um produto novo (com múltiplas variantes e
  imagens): o trigger de banco enfileira `integracao_catalogo_outbox`,
  `PublicarCatalogoCanalUseCase` chama `criar_produto` com o DTO correto e
  cria `MapeamentoVarianteCanal` para cada variante;
- atualização de um produto já publicado (ex. mudar preço de uma variante):
  chama `atualizar_produto` (não `criar_produto`) usando o
  `produto_externo_id` já mapeado;
- coalescing (design §4.2): múltiplas edições rápidas no mesmo produto
  geram múltiplas linhas de outbox, mas só uma chamada HTTP é feita;
- uma variante nova adicionada a um produto já publicado: só essa variante
  ganha um `MapeamentoVarianteCanal` novo, sem republicar do zero via
  `criar_produto` (a chamada é `atualizar_produto`);
- retry com backoff exponencial + jitter em falha transitória (5xx), mesma
  política compartilhada com o outbox de estoque (`_backoff_outbox.py`).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyImagemRepository,
    SqlAlchemyVarianteRepository,
)
from amactive.contexts.integracao_canais.application.use_cases.publicar_catalogo_canal import (
    PublicarCatalogoCanalUseCase,
)
from amactive.contexts.integracao_canais.domain.entities import CanalIntegracao
from amactive.contexts.integracao_canais.domain.exceptions import NuvemshopIndisponivel
from amactive.contexts.integracao_canais.domain.repositories import (
    NuvemshopPedidoDTO,
    ProdutoParaPublicacao,
    PublicacaoResultado,
)
from amactive.contexts.integracao_canais.infrastructure.gateways.catalogo_gateway import (
    CatalogoIntegracaoGateway,
)
from amactive.contexts.integracao_canais.infrastructure.persistence.repositories import (
    SqlAlchemyIntegracaoCatalogoOutboxRepository,
    SqlAlchemyMapeamentoVarianteRepository,
)

pytestmark = pytest.mark.integration

# Ver docstring equivalente em test_publicar_estoque_canal.py — `db_session`
# isola cada teste, mas pelo menos um outro teste do repositório deixa dados
# reais committados via uma sessão fora da transação externa. Os testes
# abaixo nunca dependem de serem os únicos dados na fila.
_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS = 100_000


class _NuvemshopClientCatalogoFake:
    """Fake mínimo de `NuvemshopClientPort` — só `criar_produto`/
    `atualizar_produto` são exercidos por `PublicarCatalogoCanalUseCase`; os
    demais métodos do Protocol existem apenas para satisfazer a assinatura
    estrutural.

    `falha_na_primeira_chamada_do_produto`: identifica UM `produto_id`
    (AMACTIVE) e uma exceção a levantar na primeira chamada (criação OU
    atualização, o que vier primeiro) referente a ESSE produto — chamadas de
    QUALQUER outro produto nunca falham. Deliberadamente NÃO indexado pela
    N-ésima chamada global (diferente de `_NuvemshopClientEstoqueFake`,
    cujos testes processam só a variante do próprio teste): o lote de
    `executar(limite=_LIMITE_GRANDE_...)` pode incluir produtos de OUTROS
    testes (dados reais deixados por `test_api_fluxo_completo.py`, ver
    comentário no topo do módulo) processados antes do produto do teste
    atual, então um índice global seria não-determinístico.

    IDs externos de produto/variante são atribuídos deterministicamente a
    cada chamada bem-sucedida (`produto-N`), e variantes são casadas por
    `sku` (mesmo critério real de `mappers.mapear_resultado_publicacao`)."""

    def __init__(
        self, *, falha_na_primeira_chamada_do_produto: tuple[UUID, Exception] | None = None
    ) -> None:
        self.chamadas_criar: list[ProdutoParaPublicacao] = []
        self.chamadas_atualizar: list[tuple[str, ProdutoParaPublicacao]] = []
        if falha_na_primeira_chamada_do_produto is not None:
            self._produto_id_com_falha, self._excecao = falha_na_primeira_chamada_do_produto
        else:
            self._produto_id_com_falha, self._excecao = None, None
        self._ja_falhou = False
        self._proximo_id = 1

    async def buscar_pedido(self, pedido_externo_id: str) -> NuvemshopPedidoDTO:
        raise NotImplementedError("Não exercido por PublicarCatalogoCanalUseCase.")

    async def criar_produto(self, produto: ProdutoParaPublicacao) -> PublicacaoResultado:
        self.chamadas_criar.append(produto)
        self._levantar_se_necessario(produto)
        produto_externo_id = f"produto-{self._proximo_id}"
        self._proximo_id += 1
        return self._resultado(produto_externo_id, produto)

    async def atualizar_produto(
        self, produto_externo_id: str, produto: ProdutoParaPublicacao
    ) -> PublicacaoResultado:
        self.chamadas_atualizar.append((produto_externo_id, produto))
        self._levantar_se_necessario(produto)
        return self._resultado(produto_externo_id, produto)

    async def atualizar_estoque_variante(
        self, *, produto_externo_id: str, variante_externo_id: str, quantidade: int
    ) -> None:
        raise NotImplementedError("Não exercido por PublicarCatalogoCanalUseCase.")

    def _levantar_se_necessario(self, produto: ProdutoParaPublicacao) -> None:
        if (
            not self._ja_falhou
            and self._produto_id_com_falha is not None
            and produto.produto_id == self._produto_id_com_falha
        ):
            self._ja_falhou = True
            assert self._excecao is not None
            raise self._excecao

    @staticmethod
    def _resultado(produto_externo_id: str, produto: ProdutoParaPublicacao) -> PublicacaoResultado:
        return PublicacaoResultado(
            produto_externo_id=produto_externo_id,
            variantes_externo_id={
                str(variante.variante_id): f"variante-{variante.sku}"
                for variante in produto.variantes
            },
        )


def _use_case(
    db_session: AsyncSession, client: _NuvemshopClientCatalogoFake
) -> PublicarCatalogoCanalUseCase:
    return PublicarCatalogoCanalUseCase(
        nuvemshop_client=client,
        catalogo_integracao_port=CatalogoIntegracaoGateway(db_session),
        mapeamento_variante_repository=SqlAlchemyMapeamentoVarianteRepository(db_session),
        outbox_repository=SqlAlchemyIntegracaoCatalogoOutboxRepository(db_session),
    )


async def _status_outbox_do_produto(
    db_session: AsyncSession, produto_id: UUID
) -> list[dict[str, object]]:
    resultado = await db_session.execute(
        text(
            "SELECT id, status, tentativas, proxima_tentativa_em "
            "FROM integracao_catalogo_outbox WHERE produto_id = :produto_id "
            "ORDER BY criado_em"
        ),
        {"produto_id": produto_id},
    )
    return [dict(linha) for linha in resultado.mappings().all()]


async def _empurrar_criado_em_das_linhas_novas(
    db_session: AsyncSession, *, produto_id: UUID, ids_ja_vistos: set[UUID], segundos: float
) -> set[UUID]:
    """Mesmo propósito de `_empurrar_criado_em_das_linhas_novas` em
    test_publicar_estoque_canal.py — só para setup determinístico de teste,
    NUNCA usado pela aplicação. Ver docstring daquele módulo para o porquê
    (o Postgres congela `now()` no início da transação, não por statement)."""
    resultado = await db_session.execute(
        text("SELECT id FROM integracao_catalogo_outbox WHERE produto_id = :produto_id"),
        {"produto_id": produto_id},
    )
    todos_ids = {linha[0] for linha in resultado.all()}
    novos_ids = todos_ids - ids_ja_vistos
    if novos_ids:
        await db_session.execute(
            text(
                "UPDATE integracao_catalogo_outbox "
                "SET criado_em = now() + make_interval(secs => :segundos) "
                "WHERE id = ANY(:ids)"
            ),
            {"segundos": segundos, "ids": list(novos_ids)},
        )
    return todos_ids


def _chamadas_para_produto(
    client: _NuvemshopClientCatalogoFake, produto_id: UUID
) -> tuple[list[ProdutoParaPublicacao], list[tuple[str, ProdutoParaPublicacao]]]:
    """Filtra as chamadas do fake pelo `produto_id` do teste.

    Necessário porque `executar(limite=_LIMITE_GRANDE_...)` processa TODO o
    lote coalescido pendente — diferente do outbox de estoque (onde uma
    variante sem `MapeamentoVarianteCanal` é marcada `ENVIADO` sem chamar o
    client, ver `publicar_estoque_canal.py`), aqui QUALQUER produto pendente
    sem mapeamento gera uma chamada HTTP real. Dados reais deixados por
    outros testes (ver comentário no topo do módulo) fariam o client
    acumular chamadas de OUTROS produtos além do testado aqui."""
    criadas = [p for p in client.chamadas_criar if p.produto_id == produto_id]
    atualizadas = [
        (produto_externo_id, p)
        for produto_externo_id, p in client.chamadas_atualizar
        if p.produto_id == produto_id
    ]
    return criadas, atualizadas


async def test_primeira_publicacao_cria_produto_com_variantes_e_imagens_e_mapeia_cada_variante(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante1 = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="100.00")
    variante2 = await SqlAlchemyVarianteRepository(db_session).criar(
        produto_id=variante1.produto_id,
        sku=f"{variante1.sku}-G",
        tamanho="G",
        cor=variante1.cor,
        preco_venda=Decimal("110.00"),
        preco_custo=None,
    )
    await SqlAlchemyImagemRepository(db_session).criar(
        produto_id=variante1.produto_id,
        cor=variante1.cor,
        url="/media/produto-1.jpg",
        ordem=0,
        principal=True,
    )
    await db_session.commit()

    linhas_antes = await _status_outbox_do_produto(db_session, variante1.produto_id)
    assert len(linhas_antes) >= 1
    assert all(linha["status"] == "PENDENTE" for linha in linhas_antes)

    client = _NuvemshopClientCatalogoFake()
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1  # >= pois pode incluir linhas pre-existentes de outros testes
    # Coalescing: N linhas de outbox para o mesmo produto (INSERT do
    # produto + INSERT de cada variante + INSERT da imagem), mas só 1
    # chamada HTTP — sempre `criar_produto`, nunca `atualizar_produto`,
    # nesta primeira publicação.
    criadas, atualizadas = _chamadas_para_produto(client, variante1.produto_id)
    assert len(criadas) == 1
    assert atualizadas == []

    produto_enviado = criadas[0]
    assert produto_enviado.produto_id == variante1.produto_id
    assert {v.variante_id for v in produto_enviado.variantes} == {variante1.id, variante2.id}
    assert len(produto_enviado.imagens) == 1
    assert produto_enviado.imagens[0].url == "/media/produto-1.jpg"

    mapeamentos = SqlAlchemyMapeamentoVarianteRepository(db_session)
    mapeamento1 = await mapeamentos.buscar_por_variante_id(
        variante_id=variante1.id, canal=CanalIntegracao.NUVEMSHOP
    )
    mapeamento2 = await mapeamentos.buscar_por_variante_id(
        variante_id=variante2.id, canal=CanalIntegracao.NUVEMSHOP
    )
    assert mapeamento1 is not None
    assert mapeamento2 is not None
    assert mapeamento1.produto_externo_id == mapeamento2.produto_externo_id

    linhas_depois = await _status_outbox_do_produto(db_session, variante1.produto_id)
    assert all(linha["status"] == "ENVIADO" for linha in linhas_depois)


async def test_atualizacao_de_produto_ja_publicado_chama_atualizar_produto(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5, preco_venda="50.00")
    await db_session.commit()

    # Primeira publicação — fora do escopo da asserção deste teste, só setup.
    client_inicial = _NuvemshopClientCatalogoFake()
    await _use_case(db_session, client_inicial).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()
    criadas_inicial, _ = _chamadas_para_produto(client_inicial, variante.produto_id)
    assert len(criadas_inicial) == 1
    mapeamentos = SqlAlchemyMapeamentoVarianteRepository(db_session)
    mapeamento_original = await mapeamentos.buscar_por_variante_id(
        variante_id=variante.id, canal=CanalIntegracao.NUVEMSHOP
    )
    assert mapeamento_original is not None

    # Muda o preço da variante — enfileira uma nova linha ATUALIZAR.
    await SqlAlchemyVarianteRepository(db_session).atualizar(
        variante.id, preco_venda=Decimal("59.90")
    )
    await db_session.commit()

    linhas = await _status_outbox_do_produto(db_session, variante.produto_id)
    assert any(linha["status"] == "PENDENTE" for linha in linhas)

    client = _NuvemshopClientCatalogoFake()
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1
    criadas, atualizadas = _chamadas_para_produto(client, variante.produto_id)
    assert criadas == []  # nunca republica do zero
    assert len(atualizadas) == 1
    produto_externo_id_usado, produto_enviado = atualizadas[0]
    mapeamento_depois = await mapeamentos.buscar_por_variante_id(
        variante_id=variante.id, canal=CanalIntegracao.NUVEMSHOP
    )
    assert mapeamento_depois is not None
    # `atualizar_produto` sempre usa o `produto_externo_id` JÁ mapeado —
    # nunca gera um novo ID externo (o mock devolveria um `produto-N`
    # diferente se o use case chamasse `criar_produto` por engano).
    assert produto_externo_id_usado == mapeamento_original.produto_externo_id
    assert mapeamento_depois.produto_externo_id == mapeamento_original.produto_externo_id
    assert produto_enviado.produto_id == variante.produto_id
    assert produto_enviado.variantes[0].preco_venda == Decimal("59.90")


async def test_coalescing_duas_edicoes_rapidas_geram_uma_unica_chamada_http(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5, preco_venda="20.00")
    await db_session.commit()
    ids_vistos = await _empurrar_criado_em_das_linhas_novas(
        db_session, produto_id=variante.produto_id, ids_ja_vistos=set(), segundos=1
    )

    variante_repo = SqlAlchemyVarianteRepository(db_session)
    for indice, novo_preco in enumerate((Decimal("21.00"), Decimal("22.00"))):
        await variante_repo.atualizar(variante.id, preco_venda=novo_preco)
        await db_session.commit()
        ids_vistos = await _empurrar_criado_em_das_linhas_novas(
            db_session,
            produto_id=variante.produto_id,
            ids_ja_vistos=ids_vistos,
            segundos=2 + indice,
        )

    # 2 linhas da criação do produto/variante (fixture, trigger de produto +
    # trigger de variante) + 2 das edições de preço rápidas acima = 4 linhas
    # PENDENTE para o mesmo produto.
    linhas_antes = await _status_outbox_do_produto(db_session, variante.produto_id)
    assert len(linhas_antes) == 4

    client = _NuvemshopClientCatalogoFake()
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1
    # Só 1 chamada HTTP no total para ESTE produto (criação, já que era a
    # primeira publicação), mesmo com 4 linhas de outbox coalescidas — e com
    # o preço mais RECENTE (22.00, não um valor intermediário).
    criadas, atualizadas = _chamadas_para_produto(client, variante.produto_id)
    assert len(criadas) + len(atualizadas) == 1
    produtos_enviados = criadas or [c for _, c in atualizadas]
    assert produtos_enviados[0].variantes[0].preco_venda == Decimal("22.00")

    linhas_depois = await _status_outbox_do_produto(db_session, variante.produto_id)
    assert len(linhas_depois) == 4
    assert all(linha["status"] == "ENVIADO" for linha in linhas_depois)


async def test_variante_nova_em_produto_ja_publicado_so_mapeia_a_nova_sem_criar_produto(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante1 = await criar_variante_com_estoque(quantidade_inicial=5, preco_venda="30.00")
    await db_session.commit()

    client_inicial = _NuvemshopClientCatalogoFake()
    await _use_case(db_session, client_inicial).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()
    criadas_inicial, _ = _chamadas_para_produto(client_inicial, variante1.produto_id)
    assert len(criadas_inicial) == 1

    mapeamentos = SqlAlchemyMapeamentoVarianteRepository(db_session)
    mapeamento1_antes = await mapeamentos.buscar_por_variante_id(
        variante_id=variante1.id, canal=CanalIntegracao.NUVEMSHOP
    )
    assert mapeamento1_antes is not None

    # Variante nova adicionada DEPOIS da primeira publicação — enfileira
    # ATUALIZAR (trigger de produto_variante).
    variante2 = await SqlAlchemyVarianteRepository(db_session).criar(
        produto_id=variante1.produto_id,
        sku=f"{variante1.sku}-P",
        tamanho="P",
        cor=variante1.cor,
        preco_venda=Decimal("28.00"),
        preco_custo=None,
    )
    await db_session.commit()

    client = _NuvemshopClientCatalogoFake()
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1
    criadas, atualizadas = _chamadas_para_produto(client, variante1.produto_id)
    assert criadas == []  # nunca republica do zero via criar_produto
    assert len(atualizadas) == 1

    mapeamento1_depois = await mapeamentos.buscar_por_variante_id(
        variante_id=variante1.id, canal=CanalIntegracao.NUVEMSHOP
    )
    mapeamento2 = await mapeamentos.buscar_por_variante_id(
        variante_id=variante2.id, canal=CanalIntegracao.NUVEMSHOP
    )
    assert mapeamento1_depois is not None
    assert mapeamento2 is not None
    # A variante já mapeada mantém o mesmo produto_externo_id (upsert
    # idempotente, não regrava do zero); a nova ganha o mesmo produto.
    assert mapeamento1_depois.produto_externo_id == mapeamento1_antes.produto_externo_id
    assert mapeamento2.produto_externo_id == mapeamento1_antes.produto_externo_id


async def test_falha_5xx_agenda_retry_com_backoff_e_jitter(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    await db_session.commit()

    client = _NuvemshopClientCatalogoFake(
        falha_na_primeira_chamada_do_produto=(
            variante.produto_id,
            NuvemshopIndisponivel("Erro transitório da Nuvemshop.", status_code_origem=500),
        )
    )
    antes = datetime.now(UTC)
    processados = await _use_case(db_session, client).executar(
        limite=_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS
    )
    await db_session.commit()

    assert processados >= 1
    criadas, _ = _chamadas_para_produto(client, variante.produto_id)
    assert len(criadas) == 1

    # `marcar_erro_com_retry` (diferente de `marcar_enviado`) NÃO supersede
    # linhas irmãs do mesmo `produto_id` — só a linha "líder" que de fato
    # foi processada pela consulta de coalescing recebe o retry; eventuais
    # outras linhas PENDENTE pré-existentes do mesmo produto (ex.: a linha
    # de criação da variante, enfileirada pelo fixture junto com a linha de
    # criação do produto) permanecem como estavam.
    linhas = await _status_outbox_do_produto(db_session, variante.produto_id)
    linhas_com_erro = [linha for linha in linhas if linha["status"] == "ERRO"]
    assert len(linhas_com_erro) == 1
    assert linhas_com_erro[0]["tentativas"] == 1
    proxima_tentativa_em = linhas_com_erro[0]["proxima_tentativa_em"]
    assert proxima_tentativa_em is not None
    # tentativa 1 -> 2s base, ±20% de jitter (design §4.3): folga generosa
    # para não deixar o teste flaky por tempo de execução do próprio teste.
    atraso = (proxima_tentativa_em - antes).total_seconds()
    assert 1.0 < atraso < 10.0
