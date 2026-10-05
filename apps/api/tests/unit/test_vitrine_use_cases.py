"""Testes unitários das regras da vitrine (checkout com reserva, expiração,
confirmação de pagamento e cancelamento de pedido pendente) — fakes em memória.

O comportamento real contra o Postgres (FOR UPDATE, triggers de estoque, filtros
de disponibilidade) fica em tests/integration/test_vitrine_reserva.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from amactive.contexts.vendas.application.dto import PagamentoInput
from amactive.contexts.vendas.application.use_cases.cancelar_pedido import CancelarPedidoUseCase
from amactive.contexts.vendas.application.use_cases.confirmar_pagamento_vitrine import (
    ConfirmarPagamentoVitrineUseCase,
)
from amactive.contexts.vendas.application.use_cases.criar_pedido_vitrine import (
    PRAZO_RESERVA_PADRAO,
    CriarPedidoVitrineUseCase,
    ItemVitrineInput,
)
from amactive.contexts.vendas.domain.entities import (
    FormaPagamento,
    ItemPedido,
    OrigemCanalPedido,
    Pedido,
    StatusPedido,
)
from amactive.contexts.vendas.domain.exceptions import (
    ItensVitrineInvalidos,
    PagamentosNaoConferem,
    PedidoNaoAguardandoPagamento,
    ReservaVencida,
    VarianteDeVendaInvalida,
)
from amactive.contexts.vendas.domain.repositories import VarianteVenda
from amactive.contexts.vendas.infrastructure.api.schemas import CriarPedidoRequest
from amactive.shared_kernel.exceptions import ErroDeValidacao, EstoqueInsuficiente

pytestmark = pytest.mark.unit

AGORA = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
USUARIO = uuid4()


@dataclass
class _CatalogoFake:
    variantes: dict[UUID, VarianteVenda]

    async def buscar_variante_para_venda(self, variante_id: UUID) -> VarianteVenda | None:
        return self.variantes.get(variante_id)


@dataclass
class _EstoqueFake:
    saldos: dict[UUID, int]
    saidas: list[tuple[UUID, int]] = field(default_factory=list)
    devolucoes: list[tuple[UUID, int]] = field(default_factory=list)

    async def saldo_bloqueado(self, variante_id: UUID) -> int:
        return self.saldos.get(variante_id, 0)

    async def registrar_saida_venda(
        self, *, variante_id, quantidade, pedido_id, usuario_id
    ) -> None:
        self.saidas.append((variante_id, quantidade))
        self.saldos[variante_id] = self.saldos.get(variante_id, 0) - quantidade

    async def registrar_entrada_devolucao(
        self, *, variante_id, quantidade, pedido_id, usuario_id
    ) -> None:
        self.devolucoes.append((variante_id, quantidade))


@dataclass
class _ClienteFake:
    telefones: list[str] = field(default_factory=list)

    async def obter_ou_criar_por_telefone(self, *, nome: str, telefone: str) -> UUID:
        self.telefones.append(telefone)
        return uuid4()


@dataclass
class _PedidoRepoFake:
    pedidos: dict[UUID, Pedido] = field(default_factory=dict)
    contador: int = 0
    pagamentos_adicionados: list[dict] = field(default_factory=list)

    async def proximo_numero(self) -> str:
        self.contador += 1
        return f"PED-{self.contador:06d}"

    async def criar(self, **kwargs) -> Pedido:
        pedido = Pedido(
            id=uuid4(),
            numero=kwargs["numero"],
            cliente_id=kwargs["cliente_id"],
            usuario_id=kwargs["usuario_id"],
            status=kwargs["status"],
            subtotal=kwargs["subtotal"],
            desconto=kwargs["desconto"],
            valor_total=kwargs["valor_total"],
            observacao=kwargs["observacao"],
            criado_em=AGORA,
            confirmado_em=kwargs["confirmado_em"],
            cancelado_em=None,
            origem_canal=kwargs["origem_canal"],
            pedido_externo_id=kwargs["pedido_externo_id"],
            reservado_ate=kwargs.get("reservado_ate"),
            itens=[
                ItemPedido(
                    id=uuid4(),
                    variante_id=i["variante_id"],
                    sku=i["sku"],
                    quantidade=i["quantidade"],
                    preco_unitario=i["preco_unitario"],
                    desconto_item=i["desconto_item"],
                    subtotal=i["subtotal"],
                )
                for i in kwargs["itens"]
            ],
        )
        self.pedidos[pedido.id] = pedido
        return pedido

    async def buscar_por_id(self, pedido_id: UUID) -> Pedido | None:
        return self.pedidos.get(pedido_id)

    async def adicionar_pagamentos(self, pedido_id: UUID, pagamentos: list[dict]) -> None:
        self.pagamentos_adicionados.extend(pagamentos)

    async def atualizar_status(self, pedido_id, *, status, timestamp) -> None:
        pedido = self.pedidos[pedido_id]
        # Pedido é dataclass congelada: recriamos com o status novo.
        atualizado = Pedido(
            **{
                **pedido.__dict__,
                "status": status,
                "reservado_ate": None if status != StatusPedido.PENDENTE else pedido.reservado_ate,
                "confirmado_em": timestamp
                if status == StatusPedido.CONFIRMADO
                else pedido.confirmado_em,
                "cancelado_em": timestamp
                if status == StatusPedido.CANCELADO
                else pedido.cancelado_em,
            }
        )
        self.pedidos[pedido_id] = atualizado


@dataclass
class _ReservasFake:
    """Mesma semântica da tabela `reserva_estoque` + índice de vigência."""

    pedidos: _PedidoRepoFake
    reservas: list[tuple[UUID, UUID, int]] = field(default_factory=list)  # (pedido, variante, qtd)

    def _vigente(self, pedido_id: UUID, agora: datetime) -> bool:
        pedido = self.pedidos.pedidos.get(pedido_id)
        return (
            pedido is not None
            and pedido.status == StatusPedido.PENDENTE
            and pedido.reservado_ate is not None
            and pedido.reservado_ate > agora
        )

    async def quantidade_reservada_ativa(self, variante_id: UUID, *, agora: datetime) -> int:
        return sum(
            qtd
            for pid, vid, qtd in self.reservas
            if vid == variante_id and self._vigente(pid, agora)
        )

    async def registrar(self, *, pedido_id, variante_id, quantidade) -> None:
        self.reservas.append((pedido_id, variante_id, quantidade))

    async def liberar_do_pedido(self, pedido_id: UUID) -> None:
        self.reservas = [r for r in self.reservas if r[0] != pedido_id]

    async def pedidos_com_reserva_vencida(self, *, agora: datetime) -> list[UUID]:
        return [
            pid
            for pid, p in self.pedidos.pedidos.items()
            if p.status == StatusPedido.PENDENTE
            and p.reservado_ate is not None
            and p.reservado_ate <= agora
        ]


def _variante(preco: str, *, desconto: str | None = None, ativo: bool = True, nome="Legging"):
    return VarianteVenda(
        id=uuid4(),
        sku=f"SKU-{uuid4().hex[:6].upper()}",
        preco_venda=Decimal(preco),
        ativo=ativo,
        produto_nome=nome,
        desconto_percentual=Decimal(desconto) if desconto else None,
    )


@dataclass
class _Ambiente:
    catalogo: _CatalogoFake
    estoque: _EstoqueFake
    pedidos: _PedidoRepoFake
    clientes: _ClienteFake
    reservas: _ReservasFake

    def checkout(self) -> CriarPedidoVitrineUseCase:
        return CriarPedidoVitrineUseCase(
            self.pedidos, self.catalogo, self.estoque, self.clientes, self.reservas
        )


def _ambiente(*variantes_com_saldo: tuple[VarianteVenda, int]) -> _Ambiente:
    pedidos = _PedidoRepoFake()
    return _Ambiente(
        catalogo=_CatalogoFake({v.id: v for v, _ in variantes_com_saldo}),
        estoque=_EstoqueFake({v.id: saldo for v, saldo in variantes_com_saldo}),
        pedidos=pedidos,
        clientes=_ClienteFake(),
        reservas=_ReservasFake(pedidos),
    )


async def _checkout(amb: _Ambiente, *itens: tuple[VarianteVenda, int], agora=AGORA) -> Pedido:
    return await amb.checkout().executar(
        cliente_nome="Ana Cliente",
        cliente_telefone="(11) 99999-0001",
        observacao=None,
        itens=[ItemVitrineInput(v.id, q) for v, q in itens],
        agora=agora,
    )


# ── Checkout ─────────────────────────────────────────────────────────────


async def test_checkout_cria_pedido_pendente_sem_operador_e_sem_baixar_estoque() -> None:
    variante = _variante("100.00")
    amb = _ambiente((variante, 5))

    pedido = await _checkout(amb, (variante, 2))

    assert pedido.status == StatusPedido.PENDENTE
    assert pedido.origem_canal == OrigemCanalPedido.VITRINE
    assert pedido.usuario_id is None
    assert pedido.reservado_ate == AGORA + PRAZO_RESERVA_PADRAO
    assert pedido.pagamentos == []
    assert amb.estoque.saidas == []  # reserva não é baixa
    assert amb.estoque.saldos[variante.id] == 5
    assert amb.clientes.telefones == ["11999990001"]  # só dígitos


async def test_checkout_aplica_desconto_promocional_como_desconto_do_item() -> None:
    variante = _variante("100.00", desconto="10")
    amb = _ambiente((variante, 5))

    pedido = await _checkout(amb, (variante, 3))

    item = pedido.itens[0]
    assert item.preco_unitario == Decimal("100.00")
    assert item.desconto_item == Decimal("30.00")  # 10% de 3 x 100
    assert item.subtotal == Decimal("270.00")
    assert pedido.valor_total == Decimal("270.00")


async def test_reserva_considera_unidades_ja_reservadas_por_outros_pedidos() -> None:
    variante = _variante("50.00")
    amb = _ambiente((variante, 5))
    await _checkout(amb, (variante, 3))

    with pytest.raises(EstoqueInsuficiente, match="restam 2"):
        await _checkout(amb, (variante, 3))

    # As 2 restantes ainda podem ser pedidas.
    pedido = await _checkout(amb, (variante, 2))
    assert pedido.status == StatusPedido.PENDENTE


async def test_reserva_vencida_deixa_de_contar_e_e_limpa_no_checkout_seguinte() -> None:
    variante = _variante("50.00")
    amb = _ambiente((variante, 5))
    antigo = await _checkout(
        amb, (variante, 5), agora=AGORA - PRAZO_RESERVA_PADRAO - timedelta(minutes=1)
    )

    # Pedido antigo ainda estava dentro do prazo quando foi feito; agora expirou.
    novo = await _checkout(amb, (variante, 5))

    assert novo.status == StatusPedido.PENDENTE
    assert amb.pedidos.pedidos[antigo.id].status == StatusPedido.CANCELADO
    assert amb.pedidos.pedidos[antigo.id].reservado_ate is None


async def test_carrinho_com_variante_repetida_e_rejeitado() -> None:
    variante = _variante("50.00")
    amb = _ambiente((variante, 5))

    with pytest.raises(ItensVitrineInvalidos):
        await amb.checkout().executar(
            cliente_nome="Ana",
            cliente_telefone="11999990001",
            observacao=None,
            itens=[ItemVitrineInput(variante.id, 1), ItemVitrineInput(variante.id, 1)],
            agora=AGORA,
        )


async def test_variante_inativa_nao_pode_ser_pedida() -> None:
    inativa = _variante("50.00", ativo=False)
    amb = _ambiente((inativa, 5))

    with pytest.raises(VarianteDeVendaInvalida):
        await _checkout(amb, (inativa, 1))


async def test_telefone_sem_ddd_valido_e_rejeitado() -> None:
    variante = _variante("50.00")
    amb = _ambiente((variante, 5))

    with pytest.raises(ErroDeValidacao):
        await amb.checkout().executar(
            cliente_nome="Ana",
            cliente_telefone="123",
            observacao=None,
            itens=[ItemVitrineInput(variante.id, 1)],
            agora=AGORA,
        )


# ── Confirmação de pagamento ─────────────────────────────────────────────


def _confirmar(amb: _Ambiente, pedido: Pedido, pagamentos: list[PagamentoInput], agora=AGORA):
    return ConfirmarPagamentoVitrineUseCase(amb.pedidos, amb.estoque, amb.reservas).executar(
        pedido.id, pagamentos=pagamentos, usuario_id=USUARIO, agora=agora
    )


async def test_confirmar_pagamento_baixa_estoque_libera_reserva_e_confirma() -> None:
    variante = _variante("100.00")
    amb = _ambiente((variante, 5))
    pedido = await _checkout(amb, (variante, 2))

    confirmado = await _confirmar(
        amb,
        pedido,
        [PagamentoInput(FormaPagamento.PIX, Decimal("200.00"))],
    )

    assert confirmado.status == StatusPedido.CONFIRMADO
    assert confirmado.confirmado_em == AGORA
    assert confirmado.reservado_ate is None
    assert amb.estoque.saidas == [(variante.id, 2)]
    assert amb.estoque.saldos[variante.id] == 3
    assert amb.reservas.reservas == []  # reserva removida
    assert amb.pedidos.pagamentos_adicionados == [
        {"forma_pagamento": FormaPagamento.PIX, "valor": Decimal("200.00")}
    ]


async def test_confirmar_com_soma_de_pagamentos_diferente_do_total_falha() -> None:
    variante = _variante("100.00")
    amb = _ambiente((variante, 5))
    pedido = await _checkout(amb, (variante, 2))

    with pytest.raises(PagamentosNaoConferem):
        await _confirmar(amb, pedido, [PagamentoInput(FormaPagamento.PIX, Decimal("199.99"))])

    assert amb.estoque.saidas == []
    assert amb.pedidos.pedidos[pedido.id].status == StatusPedido.PENDENTE


async def test_confirmar_com_reserva_vencida_e_bloqueado_sem_baixar_estoque() -> None:
    variante = _variante("100.00")
    amb = _ambiente((variante, 5))
    pedido = await _checkout(amb, (variante, 2))

    with pytest.raises(ReservaVencida):
        await _confirmar(
            amb,
            pedido,
            [PagamentoInput(FormaPagamento.PIX, Decimal("200.00"))],
            agora=AGORA + PRAZO_RESERVA_PADRAO,
        )
    assert amb.estoque.saidas == []


async def test_confirmar_pedido_ja_confirmado_falha() -> None:
    variante = _variante("100.00")
    amb = _ambiente((variante, 5))
    pedido = await _checkout(amb, (variante, 1))
    await _confirmar(amb, pedido, [PagamentoInput(FormaPagamento.PIX, Decimal("100.00"))])

    with pytest.raises(PedidoNaoAguardandoPagamento):
        await _confirmar(amb, pedido, [PagamentoInput(FormaPagamento.PIX, Decimal("100.00"))])


async def test_confirmar_pedido_que_nao_e_da_vitrine_falha() -> None:
    variante = _variante("100.00")
    amb = _ambiente((variante, 5))
    pedido = await _checkout(amb, (variante, 1))
    # Simula um pedido de outro canal com a mesma forma (PENDENTE sem operador).
    amb.pedidos.pedidos[pedido.id] = Pedido(
        **{**pedido.__dict__, "origem_canal": OrigemCanalPedido.PDV}
    )

    with pytest.raises(PedidoNaoAguardandoPagamento):
        await _confirmar(amb, pedido, [PagamentoInput(FormaPagamento.PIX, Decimal("100.00"))])


# ── Cancelamento ─────────────────────────────────────────────────────────


async def test_cancelar_pedido_pendente_libera_reserva_sem_estornar_estoque() -> None:
    variante = _variante("100.00")
    amb = _ambiente((variante, 5))
    pedido = await _checkout(amb, (variante, 2))

    cancelado = await CancelarPedidoUseCase(amb.pedidos, amb.estoque, amb.reservas).executar(
        pedido.id, usuario_id=USUARIO
    )

    assert cancelado.status == StatusPedido.CANCELADO
    assert amb.reservas.reservas == []
    assert amb.estoque.devolucoes == []  # nunca houve baixa, nada a estornar


# ── Contrato HTTP do checkout público ────────────────────────────────────


def test_checkout_publico_nao_aceita_origem_canal_nem_pagamento() -> None:
    """O payload público não tem `origem_canal`/`pagamentos`: o cliente não
    escolhe canal nem valor. Se alguém mandar esses campos, eles são ignorados
    pelo schema da vitrine e a origem continua sendo VITRINE."""
    from amactive.contexts.vitrine.infrastructure.api.schemas import CheckoutRequest

    dados = CheckoutRequest.model_validate(
        {
            "cliente": {"nome": "Ana", "telefone": "11999990001"},
            "itens": [{"variante_id": str(uuid4()), "quantidade": 1}],
            "origem_canal": "PDV",
            "pagamentos": [],
        }
    )
    assert not hasattr(dados, "origem_canal")
    assert not hasattr(dados, "pagamentos")


def test_registro_manual_nao_aceita_origem_vitrine() -> None:
    """Pedido da vitrine só nasce pelo checkout público. Pelo POST /pedidos
    (PDV) ele seria confirmado sem reserva nem pagamento."""
    from amactive.contexts.vendas.application.use_cases.registrar_pedido_manual import (
        _validar_origem_e_pedido_externo,
    )

    with pytest.raises(ErroDeValidacao):
        _validar_origem_e_pedido_externo(OrigemCanalPedido.VITRINE, None)

    # O schema do registro manual continua aceitando os canais já existentes.
    assert CriarPedidoRequest.model_fields["origem_canal"].default == OrigemCanalPedido.PDV
