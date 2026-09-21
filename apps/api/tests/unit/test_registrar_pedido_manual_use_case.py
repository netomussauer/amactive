"""Testes unitários do registro manual de pedidos por canal
(`RegistrarPedidoManualUseCase`, schema `CriarPedidoRequest` e exceção
`PedidoExternoDuplicado`) — fakes em memória, sem banco. O comportamento real
contra o Postgres (índice único, baixa de estoque, filtros) fica em
`tests/integration/test_pedidos_origem_canal.py`."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.application.use_cases.registrar_pedido_manual import (
    RegistrarPedidoManualUseCase,
)
from amactive.contexts.vendas.domain.entities import (
    FormaPagamento,
    OrigemCanalPedido,
    Pedido,
)
from amactive.contexts.vendas.domain.exceptions import PedidoExternoDuplicado
from amactive.contexts.vendas.domain.repositories import VarianteVenda
from amactive.contexts.vendas.infrastructure.api.schemas import CriarPedidoRequest
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    violou_unicidade_pedido_externo,
)
from amactive.shared_kernel.exceptions import ConflitoDeEstado, ErroDeValidacao

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
    ) -> None:  # pragma: no cover
        raise AssertionError("não deveria ser chamado ao registrar pedido")


@dataclass
class _PedidoRepositoryFake:
    """Guarda (origem, número externo) dos pedidos "gravados" para simular o
    índice único parcial de `pedido`."""

    externos: set[tuple[OrigemCanalPedido, str]] = field(default_factory=set)
    criados: list[dict] = field(default_factory=list)
    contador: int = 0

    async def proximo_numero(self) -> str:
        self.contador += 1
        return f"PED-{self.contador:06d}"

    async def existe_pedido_externo(
        self, *, origem_canal: OrigemCanalPedido, pedido_externo_id: str
    ) -> bool:
        return (origem_canal, pedido_externo_id) in self.externos

    async def criar(self, **kwargs) -> Pedido:
        self.criados.append(kwargs)
        if kwargs["pedido_externo_id"] is not None:
            self.externos.add((kwargs["origem_canal"], kwargs["pedido_externo_id"]))
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
            origem_canal=kwargs["origem_canal"],
            pedido_externo_id=kwargs["pedido_externo_id"],
        )


@dataclass
class _Cenario:
    use_case: RegistrarPedidoManualUseCase
    repo: _PedidoRepositoryFake
    estoque: _EstoqueFake
    variante: VarianteVenda


def _cenario() -> _Cenario:
    variante = VarianteVenda(id=uuid4(), sku="SKU-1", preco_venda=Decimal("100.00"), ativo=True)
    repo = _PedidoRepositoryFake()
    estoque = _EstoqueFake()
    use_case = RegistrarPedidoManualUseCase(repo, _CatalogoFake({variante.id: variante}), estoque)
    return _Cenario(use_case=use_case, repo=repo, estoque=estoque, variante=variante)


async def _registrar(
    c: _Cenario,
    origem_canal: OrigemCanalPedido | None = None,
    pedido_externo_id: str | None = None,
) -> Pedido:
    extras: dict = {}
    if origem_canal is not None:
        extras["origem_canal"] = origem_canal
    if pedido_externo_id is not None:
        extras["pedido_externo_id"] = pedido_externo_id
    return await c.use_case.executar(
        cliente_id=None,
        desconto=Decimal("0.00"),
        observacao=None,
        itens=[
            ItemPedidoInput(variante_id=c.variante.id, quantidade=2, desconto_item=Decimal("0.00"))
        ],
        pagamentos=[PagamentoInput(forma_pagamento=FormaPagamento.PIX, valor=Decimal("200.00"))],
        usuario_id=uuid4(),
        **extras,
    )


# ── regras de coerência origem x pedido_externo_id ──
async def test_padrao_e_pdv_sem_pedido_externo_como_antes() -> None:
    c = _cenario()

    pedido = await _registrar(c)

    assert pedido.origem_canal == OrigemCanalPedido.PDV
    assert pedido.pedido_externo_id is None
    assert c.estoque.chamadas_saida == [(c.variante.id, 2)]


async def test_pdv_rejeita_pedido_externo_id_sem_tocar_em_nada() -> None:
    c = _cenario()

    with pytest.raises(ErroDeValidacao):
        await _registrar(c, OrigemCanalPedido.PDV, "1234")

    assert c.repo.criados == []
    assert c.estoque.chamadas_saida == []


async def test_nuvemshop_exige_pedido_externo_id() -> None:
    c = _cenario()

    with pytest.raises(ErroDeValidacao):
        await _registrar(c, OrigemCanalPedido.NUVEMSHOP)

    assert c.repo.criados == []
    assert c.estoque.chamadas_saida == []


async def test_nuvemshop_com_pedido_externo_id_e_aceito() -> None:
    c = _cenario()

    pedido = await _registrar(c, OrigemCanalPedido.NUVEMSHOP, "#1234")

    assert pedido.origem_canal == OrigemCanalPedido.NUVEMSHOP
    assert pedido.pedido_externo_id == "#1234"


async def test_whatsapp_sem_pedido_externo_id_e_aceito() -> None:
    c = _cenario()

    pedido = await _registrar(c, OrigemCanalPedido.WHATSAPP)

    assert pedido.origem_canal == OrigemCanalPedido.WHATSAPP
    assert pedido.pedido_externo_id is None
    assert c.estoque.chamadas_saida == [(c.variante.id, 2)]


async def test_whatsapp_rejeita_pedido_externo_id_sem_tocar_em_nada() -> None:
    c = _cenario()

    with pytest.raises(ErroDeValidacao) as excinfo:
        await _registrar(c, OrigemCanalPedido.WHATSAPP, "WA-77")

    assert excinfo.value.status_code == 422
    assert "WHATSAPP" in str(excinfo.value)
    assert "pedido_externo_id" in str(excinfo.value)
    assert c.repo.criados == []
    assert c.estoque.chamadas_saida == []


async def test_pedido_externo_id_em_branco_e_rejeitado() -> None:
    c = _cenario()

    with pytest.raises(ErroDeValidacao):
        await _registrar(c, OrigemCanalPedido.NUVEMSHOP, "   ")


# ── duplicidade ──
async def test_duplicidade_mesma_origem_e_numero_levanta_conflito_sem_baixar_estoque() -> None:
    c = _cenario()
    await _registrar(c, OrigemCanalPedido.NUVEMSHOP, "1001")
    assert len(c.estoque.chamadas_saida) == 1

    with pytest.raises(PedidoExternoDuplicado) as excinfo:
        await _registrar(c, OrigemCanalPedido.NUVEMSHOP, "1001")

    assert isinstance(excinfo.value, ConflitoDeEstado)
    assert excinfo.value.status_code == 409
    assert "1001" in str(excinfo.value)
    assert "NUVEMSHOP" in str(excinfo.value)
    # Nenhum segundo pedido/baixa de estoque.
    assert len(c.repo.criados) == 1
    assert len(c.estoque.chamadas_saida) == 1


async def test_numeros_diferentes_na_mesma_origem_sao_permitidos() -> None:
    c = _cenario()

    await _registrar(c, OrigemCanalPedido.NUVEMSHOP, "1001")
    await _registrar(c, OrigemCanalPedido.NUVEMSHOP, "1002")

    assert len(c.repo.criados) == 2
    assert len(c.estoque.chamadas_saida) == 2


async def test_whatsapp_e_pdv_sem_numero_nunca_sao_considerados_duplicados() -> None:
    c = _cenario()

    await _registrar(c, OrigemCanalPedido.WHATSAPP)
    await _registrar(c, OrigemCanalPedido.WHATSAPP)
    await _registrar(c, OrigemCanalPedido.PDV)
    await _registrar(c, OrigemCanalPedido.PDV)

    assert len(c.repo.criados) == 4


# ── schema HTTP ──
def _payload(**extras) -> dict:
    return {
        "itens": [{"variante_id": str(uuid4()), "quantidade": 1}],
        "pagamentos": [{"forma_pagamento": "PIX", "valor": "10.00"}],
        **extras,
    }


def test_schema_default_e_pdv_sem_pedido_externo() -> None:
    req = CriarPedidoRequest.model_validate(_payload())

    assert req.origem_canal == OrigemCanalPedido.PDV
    assert req.pedido_externo_id is None


def test_schema_aceita_os_tres_canais() -> None:
    for canal in ("PDV", "WHATSAPP", "NUVEMSHOP"):
        assert CriarPedidoRequest.model_validate(_payload(origem_canal=canal)).origem_canal == canal


def test_schema_rejeita_origem_desconhecida() -> None:
    with pytest.raises(ValidationError):
        CriarPedidoRequest.model_validate(_payload(origem_canal="INSTAGRAM"))


def test_schema_remove_espacos_nas_pontas_do_pedido_externo_id() -> None:
    req = CriarPedidoRequest.model_validate(
        _payload(origem_canal="NUVEMSHOP", pedido_externo_id="  1234 ")
    )

    assert req.pedido_externo_id == "1234"


@pytest.mark.parametrize("valor", ["", "   ", "x" * 101])
def test_schema_rejeita_pedido_externo_id_fora_de_1_a_100(valor: str) -> None:
    with pytest.raises(ValidationError):
        CriarPedidoRequest.model_validate(
            _payload(origem_canal="NUVEMSHOP", pedido_externo_id=valor)
        )


def test_schema_aceita_pedido_externo_id_com_100_caracteres() -> None:
    req = CriarPedidoRequest.model_validate(
        _payload(origem_canal="NUVEMSHOP", pedido_externo_id="x" * 100)
    )

    assert req.pedido_externo_id == "x" * 100


# ── tradução de IntegrityError (só a violação do índice do pedido externo) ──
class _CausaAsyncpg(Exception):
    def __init__(self, constraint_name: str | None) -> None:
        super().__init__(f'duplicate key value violates unique constraint "{constraint_name}"')
        self.constraint_name = constraint_name


def _integrity_error(constraint_name: str | None) -> IntegrityError:
    orig = Exception("erro do driver")
    orig.__cause__ = _CausaAsyncpg(constraint_name)
    return IntegrityError("INSERT INTO pedido ...", None, orig)


def test_violou_unicidade_reconhece_o_indice_do_pedido_externo() -> None:
    assert violou_unicidade_pedido_externo(_integrity_error("uq_pedido_origem_canal_externo"))


@pytest.mark.parametrize("constraint", ["pedido_numero_key", "pedido_cliente_id_fkey"])
def test_violou_unicidade_ignora_outras_violacoes_de_integridade(constraint: str) -> None:
    assert not violou_unicidade_pedido_externo(_integrity_error(constraint))


def test_violou_unicidade_sem_constraint_name_cai_no_texto_da_mensagem() -> None:
    orig = Exception(
        'duplicate key value violates unique constraint "uq_pedido_origem_canal_externo"'
    )
    outra = Exception('insert or update violates foreign key constraint "pedido_cliente_id_fkey"')

    assert violou_unicidade_pedido_externo(IntegrityError("INSERT", None, orig))
    assert not violou_unicidade_pedido_externo(IntegrityError("INSERT", None, outra))
