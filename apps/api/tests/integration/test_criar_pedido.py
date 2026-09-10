"""Testes de integração de `CriarPedidoUseCase` — cobre a orquestração real
(SqlAlchemyPedidoRepository + CatalogoEstoqueGateway) contra um Postgres de
verdade, validando a regra crítica de negócio: nenhuma alteração parcial é
persistida quando qualquer item não tem saldo suficiente (ver docs/openapi.yaml
`POST /pedidos` e docs/data-model.md § Estratégia de Concorrência)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from amactive.contexts.catalogo_estoque.domain.exceptions import SaldoDeEstoqueInsuficiente
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyEstoqueRepository,
)
from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.application.use_cases.criar_pedido import CriarPedidoUseCase
from amactive.contexts.vendas.domain.entities import FormaPagamento, StatusPedido
from amactive.contexts.vendas.domain.exceptions import PagamentosNaoConferem
from amactive.contexts.vendas.infrastructure.persistence.gateways import CatalogoEstoqueGateway
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
)

pytestmark = pytest.mark.integration


def _use_case(db_session):
    gateway = CatalogoEstoqueGateway(db_session)
    return CriarPedidoUseCase(SqlAlchemyPedidoRepository(db_session), gateway, gateway)


async def test_criar_pedido_confirma_e_da_baixa_no_estoque(
    db_session, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="100.00")

    pedido = await _use_case(db_session).executar(
        cliente_id=None,
        desconto=Decimal("0.00"),
        observacao=None,
        itens=[
            ItemPedidoInput(variante_id=variante.id, quantidade=3, desconto_item=Decimal("0.00"))
        ],
        pagamentos=[PagamentoInput(forma_pagamento=FormaPagamento.PIX, valor=Decimal("300.00"))],
        usuario_id=usuario_teste.id,
    )

    assert pedido.status == StatusPedido.CONFIRMADO
    assert pedido.numero.startswith("PED-")
    assert pedido.valor_total == Decimal("300.00")

    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)
    assert estoque.quantidade == 7


async def test_criar_pedido_com_pagamento_divergente_nao_altera_estoque(
    db_session, usuario_teste, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="100.00")

    with pytest.raises(PagamentosNaoConferem):
        await _use_case(db_session).executar(
            cliente_id=None,
            desconto=Decimal("0.00"),
            observacao=None,
            itens=[
                ItemPedidoInput(
                    variante_id=variante.id, quantidade=1, desconto_item=Decimal("0.00")
                )
            ],
            pagamentos=[
                PagamentoInput(forma_pagamento=FormaPagamento.DINHEIRO, valor=Decimal("10.00"))
            ],
            usuario_id=usuario_teste.id,
        )

    # A validação de pagamentos ocorre ANTES de qualquer INSERT — nada foi tocado.
    estoque = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante.id)
    assert estoque.quantidade == 10


async def test_criar_pedido_multiplos_itens_rollback_atomico_em_saldo_insuficiente(
    db_session, usuario_teste, criar_variante_com_estoque
) -> None:
    """Regra crítica: um pedido com 2 itens, onde o 2º item não tem saldo,
    não deve deixar NENHUM traço — nem o pedido, nem a baixa do 1º item
    (que isoladamente teria saldo suficiente)."""
    variante_ok = await criar_variante_com_estoque(quantidade_inicial=10, preco_venda="50.00")
    variante_sem_saldo = await criar_variante_com_estoque(quantidade_inicial=1, preco_venda="20.00")

    itens = [
        ItemPedidoInput(variante_id=variante_ok.id, quantidade=2, desconto_item=Decimal("0.00")),
        ItemPedidoInput(
            variante_id=variante_sem_saldo.id, quantidade=5, desconto_item=Decimal("0.00")
        ),
    ]
    valor_total = Decimal("50.00") * 2 + Decimal("20.00") * 5
    pagamentos = [PagamentoInput(forma_pagamento=FormaPagamento.PIX, valor=valor_total)]

    with pytest.raises(SaldoDeEstoqueInsuficiente):
        await _use_case(db_session).executar(
            cliente_id=None,
            desconto=Decimal("0.00"),
            observacao=None,
            itens=itens,
            pagamentos=pagamentos,
            usuario_id=usuario_teste.id,
        )

    estoque_ok = await SqlAlchemyEstoqueRepository(db_session).buscar_por_variante(variante_ok.id)
    assert estoque_ok.quantidade == 10  # NÃO foi debitado — rollback atômico
