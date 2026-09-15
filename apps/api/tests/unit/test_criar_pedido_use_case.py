"""Testes unitários de `CriarPedidoUseCase` — regras de negócio puras,
com fakes em memória para `PedidoRepository`/`CatalogoPort`/`EstoquePort`
(sem banco de dados — ver docs/data-model.md para o comportamento real do
trigger, coberto pelos testes de integração)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.application.use_cases.criar_pedido import CriarPedidoUseCase
from amactive.contexts.vendas.domain.entities import (
    FormaPagamento,
    OrigemCanalPedido,
    Pedido,
    StatusPedido,
)
from amactive.contexts.vendas.domain.exceptions import (
    PagamentosNaoConferem,
    VarianteDeVendaInvalida,
)
from amactive.contexts.vendas.domain.repositories import VarianteVenda

pytestmark = pytest.mark.unit


@dataclass
class _CatalogoFake:
    variantes: dict[UUID, VarianteVenda]

    async def buscar_variante_para_venda(self, variante_id: UUID) -> VarianteVenda | None:
        return self.variantes.get(variante_id)


@dataclass
class _EstoqueFake:
    chamadas_saida: list[tuple[UUID, int]] = field(default_factory=list)

    async def registrar_saida_venda(
        self, *, variante_id, quantidade, pedido_id, usuario_id
    ) -> None:
        self.chamadas_saida.append((variante_id, quantidade))

    async def registrar_entrada_devolucao(
        self, *, variante_id, quantidade, pedido_id, usuario_id
    ) -> None:
        raise AssertionError("não deveria ser chamado em criar_pedido")


@dataclass
class _PedidoRepositoryFake:
    contador: int = 0

    async def proximo_numero(self) -> str:
        self.contador += 1
        return f"PED-{self.contador:06d}"

    async def criar(self, **kwargs) -> Pedido:
        return Pedido(
            id=uuid4(),
            numero=kwargs["numero"],
            cliente_id=kwargs["cliente_id"],
            usuario_id=kwargs["usuario_id"],
            status=kwargs["status"],
            subtotal=kwargs["subtotal"],
            desconto=kwargs["desconto"],
            valor_total=kwargs["valor_total"],
            observacao=kwargs["observacao"],
            criado_em=datetime.now(UTC),
            confirmado_em=kwargs["confirmado_em"],
            cancelado_em=None,
            origem_canal=kwargs.get("origem_canal", OrigemCanalPedido.PDV),
            pedido_externo_id=kwargs.get("pedido_externo_id"),
        )

    async def buscar_por_id(self, pedido_id):  # pragma: no cover - não usado nestes testes
        raise NotImplementedError

    async def listar(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    async def atualizar_status(self, pedido_id, *, status, timestamp):  # pragma: no cover
        raise NotImplementedError


def _variante(preco: str, *, ativo: bool = True) -> VarianteVenda:
    return VarianteVenda(
        id=uuid4(), sku=f"SKU-{uuid4().hex[:6]}", preco_venda=Decimal(preco), ativo=ativo
    )


async def test_soma_pagamentos_deve_ser_igual_ao_valor_total() -> None:
    variante = _variante("100.00")
    use_case = CriarPedidoUseCase(
        _PedidoRepositoryFake(), _CatalogoFake({variante.id: variante}), _EstoqueFake()
    )

    with pytest.raises(PagamentosNaoConferem):
        await use_case.executar(
            cliente_id=None,
            desconto=Decimal("0.00"),
            observacao=None,
            itens=[
                ItemPedidoInput(
                    variante_id=variante.id, quantidade=1, desconto_item=Decimal("0.00")
                )
            ],
            pagamentos=[PagamentoInput(forma_pagamento=FormaPagamento.PIX, valor=Decimal("50.00"))],
            usuario_id=uuid4(),
        )


async def test_variante_inexistente_ou_inativa_e_rejeitada() -> None:
    variante_inativa = _variante("10.00", ativo=False)
    use_case = CriarPedidoUseCase(
        _PedidoRepositoryFake(),
        _CatalogoFake({variante_inativa.id: variante_inativa}),
        _EstoqueFake(),
    )

    with pytest.raises(VarianteDeVendaInvalida):
        await use_case.executar(
            cliente_id=None,
            desconto=Decimal("0.00"),
            observacao=None,
            itens=[
                ItemPedidoInput(
                    variante_id=variante_inativa.id, quantidade=1, desconto_item=Decimal("0.00")
                )
            ],
            pagamentos=[PagamentoInput(forma_pagamento=FormaPagamento.PIX, valor=Decimal("10.00"))],
            usuario_id=uuid4(),
        )


async def test_itens_de_estoque_sao_baixados_em_ordem_de_variante_id() -> None:
    v1 = _variante("10.00")
    v2 = _variante("20.00")
    # Descobre qual dos dois tem o UUID lexicograficamente maior/menor para
    # montar o request fora de ordem e verificar que o use case reordena.
    maior, menor = (v1, v2) if str(v1.id) > str(v2.id) else (v2, v1)

    catalogo = _CatalogoFake({maior.id: maior, menor.id: menor})
    estoque = _EstoqueFake()
    use_case = CriarPedidoUseCase(_PedidoRepositoryFake(), catalogo, estoque)

    valor_total = maior.preco_venda + menor.preco_venda
    await use_case.executar(
        cliente_id=None,
        desconto=Decimal("0.00"),
        observacao=None,
        # Propositalmente enviado fora de ordem (maior primeiro).
        itens=[
            ItemPedidoInput(variante_id=maior.id, quantidade=1, desconto_item=Decimal("0.00")),
            ItemPedidoInput(variante_id=menor.id, quantidade=1, desconto_item=Decimal("0.00")),
        ],
        pagamentos=[PagamentoInput(forma_pagamento=FormaPagamento.DINHEIRO, valor=valor_total)],
        usuario_id=uuid4(),
    )

    ids_chamados = [variante_id for variante_id, _ in estoque.chamadas_saida]
    assert ids_chamados == [menor.id, maior.id]


async def test_valor_total_e_subtotal_menos_desconto_do_pedido() -> None:
    variante = _variante("50.00")
    use_case = CriarPedidoUseCase(
        _PedidoRepositoryFake(), _CatalogoFake({variante.id: variante}), _EstoqueFake()
    )

    pedido = await use_case.executar(
        cliente_id=None,
        desconto=Decimal("5.00"),
        observacao=None,
        itens=[
            ItemPedidoInput(variante_id=variante.id, quantidade=2, desconto_item=Decimal("0.00"))
        ],
        pagamentos=[PagamentoInput(forma_pagamento=FormaPagamento.PIX, valor=Decimal("95.00"))],
        usuario_id=uuid4(),
    )

    assert pedido.subtotal == Decimal("100.00")
    assert pedido.valor_total == Decimal("95.00")
    assert pedido.status == StatusPedido.CONFIRMADO
