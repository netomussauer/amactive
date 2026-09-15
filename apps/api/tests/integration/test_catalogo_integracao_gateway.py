"""Teste de integração de `CatalogoIntegracaoGateway` (implementa
`CatalogoIntegracaoPort`, somente leitura) — ver
docs/design-integracao-nuvemshop.md §3.2."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyImagemRepository,
    SqlAlchemyProdutoRepository,
    SqlAlchemyVarianteRepository,
)
from amactive.contexts.integracao_canais.domain.exceptions import (
    ProdutoNaoEncontradoParaPublicacao,
)
from amactive.contexts.integracao_canais.infrastructure.gateways.catalogo_gateway import (
    CatalogoIntegracaoGateway,
)

pytestmark = pytest.mark.integration


async def test_buscar_produto_para_publicacao_monta_dto_com_variantes_e_imagens(
    db_session, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5, preco_venda="120.00")
    await SqlAlchemyImagemRepository(db_session).criar(
        produto_id=variante.produto_id,
        cor=variante.cor,
        url="/media/produto-1.jpg",
        ordem=0,
        principal=True,
    )
    await db_session.commit()

    gateway = CatalogoIntegracaoGateway(db_session)
    dto = await gateway.buscar_produto_para_publicacao(variante.produto_id)

    assert dto.produto_id == variante.produto_id
    assert dto.nome == "Legging Fitness Teste"
    assert len(dto.variantes) == 1
    assert dto.variantes[0].variante_id == variante.id
    assert dto.variantes[0].sku == variante.sku
    assert dto.variantes[0].preco_venda == Decimal("120.00")
    assert len(dto.imagens) == 1
    assert dto.imagens[0].cor == variante.cor
    assert dto.imagens[0].url == "/media/produto-1.jpg"
    assert dto.imagens[0].principal is True


async def test_buscar_produto_para_publicacao_aplica_desconto_percentual_do_produto(
    db_session, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5, preco_venda="100.00")
    await SqlAlchemyProdutoRepository(db_session).atualizar(
        variante.produto_id, desconto_percentual=Decimal(10)
    )
    await db_session.commit()

    gateway = CatalogoIntegracaoGateway(db_session)
    dto = await gateway.buscar_produto_para_publicacao(variante.produto_id)

    # 10% de desconto sobre 100.00 -> 90.00 (design §3.2: "preço/promoção já
    # calculados").
    assert dto.variantes[0].preco_venda == Decimal("90.00")


async def test_buscar_produto_para_publicacao_exclui_variantes_inativas(
    db_session, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    await SqlAlchemyVarianteRepository(db_session).inativar(variante.id)
    await db_session.commit()

    gateway = CatalogoIntegracaoGateway(db_session)
    dto = await gateway.buscar_produto_para_publicacao(variante.produto_id)

    assert dto.variantes == []


async def test_buscar_produto_para_publicacao_produto_inexistente_levanta_excecao(
    db_session,
) -> None:
    gateway = CatalogoIntegracaoGateway(db_session)

    with pytest.raises(ProdutoNaoEncontradoParaPublicacao):
        await gateway.buscar_produto_para_publicacao(uuid4())


async def test_buscar_saldo_estoque_retorna_quantidade_atual(
    db_session, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=7)

    gateway = CatalogoIntegracaoGateway(db_session)
    saldo = await gateway.buscar_saldo_estoque(variante.id)

    assert saldo == 7


async def test_buscar_saldo_estoque_variante_sem_registro_retorna_zero(db_session) -> None:
    gateway = CatalogoIntegracaoGateway(db_session)

    saldo = await gateway.buscar_saldo_estoque(uuid4())

    assert saldo == 0
