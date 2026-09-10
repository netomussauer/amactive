"""Testes de integração de `CancelarPedidoUseCase` — estorno de estoque."""

from __future__ import annotations

from decimal import Decimal

import pytest

from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyEstoqueRepository,
)
from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.application.use_cases.cancelar_pedido import CancelarPedidoUseCase
from amactive.contexts.vendas.application.use_cases.criar_pedido import CriarPedidoUseCase
from amactive.contexts.vendas.domain.entities import FormaPagamento, StatusPedido
from amactive.contexts.vendas.domain.exceptions import PedidoJaCancelado
from amactive.contexts.vendas.infrastructure.persistence.gateways import CatalogoEstoqueGateway
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
)

pytestmark = pytest.mark.integration


async def test_cancelar_pedido_confirmado_estorna_estoque(
    db_session, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="30.00")
    gateway = CatalogoEstoqueGateway(db_session)
    pedido_repo = SqlAlchemyPedidoRepository(db_session)

    pedido = await CriarPedidoUseCase(pedido_repo, gateway, gateway).executar(
        cliente_id=None,
        desconto=Decimal("0.00"),
        observacao=None,
        itens=[
            ItemPedidoInput(variante_id=variante.id, quantidade=4, desconto_item=Decimal("0.00"))
        ],
        pagamentos=[PagamentoInput(forma_pagamento=FormaPagamento.PIX, valor=Decimal("120.00"))],
        usuario_id=usuario_teste.id,
    )
    await db_session.commit()

    estoque_pos_venda = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(
        variante.id
    )
    assert estoque_pos_venda.quantidade == 6

    pedido_cancelado = await CancelarPedidoUseCase(pedido_repo, gateway).executar(
        pedido.id, usuario_id=usuario_teste.id
    )

    assert pedido_cancelado.status == StatusPedido.CANCELADO
    assert pedido_cancelado.cancelado_em is not None

    estoque_pos_cancelamento = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(
        variante.id
    )
    assert estoque_pos_cancelamento.quantidade == 10  # estorno total


async def test_cancelar_pedido_ja_cancelado_falha(
    db_session, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=5, preco_venda="10.00")
    gateway = CatalogoEstoqueGateway(db_session)
    pedido_repo = SqlAlchemyPedidoRepository(db_session)

    pedido = await CriarPedidoUseCase(pedido_repo, gateway, gateway).executar(
        cliente_id=None,
        desconto=Decimal("0.00"),
        observacao=None,
        itens=[
            ItemPedidoInput(variante_id=variante.id, quantidade=1, desconto_item=Decimal("0.00"))
        ],
        pagamentos=[
            PagamentoInput(forma_pagamento=FormaPagamento.DINHEIRO, valor=Decimal("10.00"))
        ],
        usuario_id=usuario_teste.id,
    )
    await db_session.commit()

    await CancelarPedidoUseCase(pedido_repo, gateway).executar(
        pedido.id, usuario_id=usuario_teste.id
    )
    await db_session.commit()

    with pytest.raises(PedidoJaCancelado):
        await CancelarPedidoUseCase(pedido_repo, gateway).executar(
            pedido.id, usuario_id=usuario_teste.id
        )
