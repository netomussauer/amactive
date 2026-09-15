"""Teste de integração de `contar_pendentes` em
`SqlAlchemyIntegracaoEstoqueOutboxRepository`/`SqlAlchemyIntegracaoCatalogoOutboxRepository`
— ver docs/design-integracao-nuvemshop.md §8/§9 passo 11: alimenta o gauge
`integracao_outbox_pendente{fila="estoque"|"catalogo"}` em
`scripts/run_worker.py`.

Usa uma comparação por delta (antes/depois), não um valor absoluto — mesma
razão documentada em `tests/integration/test_publicar_estoque_canal.py`
(`_LIMITE_GRANDE_O_SUFICIENTE_PARA_IGNORAR_OUTRAS_LINHAS`): outros testes
podem deixar linhas PENDENTE/ERRO pré-existentes na mesma `db_session`
(ex.: via trigger de estoque acionado por `criar_variante_com_estoque`)."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyProdutoRepository,
)
from amactive.contexts.integracao_canais.infrastructure.persistence.repositories import (
    SqlAlchemyIntegracaoCatalogoOutboxRepository,
    SqlAlchemyIntegracaoEstoqueOutboxRepository,
)

pytestmark = pytest.mark.integration


async def test_contar_pendentes_estoque_reflete_linhas_pendente_e_erro(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    repo = SqlAlchemyIntegracaoEstoqueOutboxRepository(db_session)
    antes = await repo.contar_pendentes()

    # O trigger de estoque (`fn_enfileirar_outbox_estoque`, migration
    # 000005) já enfileira 1 linha PENDENTE ao criar a variante com saldo
    # inicial — nenhum INSERT manual necessário para exercitar a contagem.
    await criar_variante_com_estoque(quantidade_inicial=5)

    depois = await repo.contar_pendentes()
    assert depois == antes + 1


async def test_contar_pendentes_nao_conta_linhas_enviado(
    db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    repo = SqlAlchemyIntegracaoEstoqueOutboxRepository(db_session)
    antes = await repo.contar_pendentes()

    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    lote = await repo.buscar_lote_pendente_coalescido(limite=1_000_000)
    linha_da_variante = next(item for item in lote if item.variante_id == variante.id)
    await repo.marcar_enviado(linha_da_variante.id, superseded_ids=[])

    depois = await repo.contar_pendentes()
    # A própria linha criada por este teste já foi marcada ENVIADO — não
    # deve contar mais do que o estado inicial (linhas de outros testes,
    # se houver, continuam intocadas).
    assert depois == antes


async def test_contar_pendentes_catalogo_reflete_linhas_pendente(
    db_session: AsyncSession,
) -> None:
    repo = SqlAlchemyIntegracaoCatalogoOutboxRepository(db_session)
    antes = await repo.contar_pendentes()

    # O trigger de catálogo (`fn_enfileirar_outbox_catalogo`, migration
    # 000005) enfileira 1 linha PENDENTE em todo INSERT em `produto`.
    produto_repo = SqlAlchemyProdutoRepository(db_session)
    await produto_repo.criar(
        nome="Produto Teste Outbox Catálogo",
        descricao=None,
        categoria_id=None,
        marca="AMACTIVE",
    )
    await db_session.commit()

    depois = await repo.contar_pendentes()
    assert depois == antes + 1
