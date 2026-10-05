"""Vitrine contra o Postgres real: reserva não baixa estoque, a disponibilidade
pública desconta reservas vigentes, e a baixa só acontece na confirmação.

Usa a fixture `criar_variante_com_estoque` (tests/integration/conftest.py) e a
transação isolada por teste (rollback no teardown)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel
from amactive.contexts.vendas.application.dto import PagamentoInput
from amactive.contexts.vendas.application.use_cases.confirmar_pagamento_vitrine import (
    ConfirmarPagamentoVitrineUseCase,
)
from amactive.contexts.vendas.application.use_cases.criar_pedido_vitrine import (
    PRAZO_RESERVA_PADRAO,
    CriarPedidoVitrineUseCase,
    ItemVitrineInput,
)
from amactive.contexts.vendas.domain.entities import FormaPagamento, StatusPedido
from amactive.contexts.vendas.infrastructure.persistence.gateways import (
    CatalogoEstoqueGateway,
    ClienteCadastrosGateway,
)
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
    SqlAlchemyReservaEstoqueRepository,
)
from amactive.contexts.vitrine.infrastructure.persistence import consultas

pytestmark = pytest.mark.integration

NOME_PRODUTO = "Legging Fitness Teste"


def _checkout(session: AsyncSession, variante_id, quantidade: int, agora: datetime):
    gateway = CatalogoEstoqueGateway(session)
    return CriarPedidoVitrineUseCase(
        SqlAlchemyPedidoRepository(session),
        gateway,
        gateway,
        ClienteCadastrosGateway(session),
        SqlAlchemyReservaEstoqueRepository(session),
    ).executar(
        cliente_nome="Ana Cliente",
        cliente_telefone="(11) 99999-0001",
        observacao=None,
        itens=[ItemVitrineInput(variante_id, quantidade)],
        agora=agora,
    )


async def test_reserva_nao_baixa_estoque_e_confirmacao_baixa(
    db_session: AsyncSession,
    usuario_teste: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5, preco_venda="100.00")
    agora = datetime.now(UTC)
    gateway = CatalogoEstoqueGateway(db_session)
    reservas = SqlAlchemyReservaEstoqueRepository(db_session)

    pedido = await _checkout(db_session, variante.id, 3, agora)

    assert pedido.status == StatusPedido.PENDENTE
    assert pedido.usuario_id is None
    assert pedido.reservado_ate == agora + PRAZO_RESERVA_PADRAO
    assert await gateway.saldo_bloqueado(variante.id) == 5  # saldo físico intocado
    assert await reservas.quantidade_reservada_ativa(variante.id, agora=agora) == 3

    confirmado = await ConfirmarPagamentoVitrineUseCase(
        SqlAlchemyPedidoRepository(db_session), gateway, reservas
    ).executar(
        pedido.id,
        pagamentos=[PagamentoInput(FormaPagamento.PIX, Decimal("300.00"))],
        usuario_id=usuario_teste.id,
        agora=agora,
    )

    assert confirmado.status == StatusPedido.CONFIRMADO
    assert confirmado.reservado_ate is None
    assert await gateway.saldo_bloqueado(variante.id) == 2  # baixa pelo trigger
    assert await reservas.quantidade_reservada_ativa(variante.id, agora=agora) == 0


async def test_reserva_vencida_nao_conta_na_disponibilidade(
    db_session: AsyncSession,
    usuario_teste: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    agora = datetime.now(UTC)
    reservas = SqlAlchemyReservaEstoqueRepository(db_session)
    await _checkout(db_session, variante.id, 5, agora)

    depois_do_prazo = agora + PRAZO_RESERVA_PADRAO + timedelta(minutes=1)
    assert await reservas.quantidade_reservada_ativa(variante.id, agora=depois_do_prazo) == 0


async def test_catalogo_publico_desconta_reservas_vigentes(
    db_session: AsyncSession,
    usuario_teste: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    agora = datetime.now(UTC)
    await _checkout(db_session, variante.id, 2, agora)

    produtos, total = await consultas.listar_produtos(
        db_session,
        agora=agora,
        page=1,
        per_page=60,
        categoria_id=None,
        busca=NOME_PRODUTO,
    )

    assert total == 1
    (produto,) = produtos
    (vitrine_variante,) = produto.variantes
    assert vitrine_variante.disponivel == 3  # 5 em estoque - 2 reservadas
    assert vitrine_variante.id == variante.id


async def test_produto_inativo_some_da_vitrine(
    db_session: AsyncSession,
    usuario_teste: UsuarioModel,
    criar_variante_com_estoque,
) -> None:
    from sqlalchemy import update

    from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import (
        ProdutoModel,
    )

    variante = await criar_variante_com_estoque(quantidade_inicial=5)
    await db_session.execute(
        update(ProdutoModel).where(ProdutoModel.nome == NOME_PRODUTO).values(ativo=False)
    )

    produtos, total = await consultas.listar_produtos(
        db_session,
        agora=datetime.now(UTC),
        page=1,
        per_page=60,
        categoria_id=None,
        busca=NOME_PRODUTO,
    )

    assert total == 0
    assert produtos == []
    assert variante.id is not None
