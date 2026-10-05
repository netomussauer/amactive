"""Portas (Protocols) do contexto Vendas.

`CatalogoPort`/`EstoquePort` são o lado "consumidor" do Shared Kernel
restrito descrito em docs/SDD.md §1.2: Vendas conhece apenas estas
interfaces, nunca as tabelas físicas `produto_variante`/`movimentacao_estoque`
de Catálogo & Estoque. A implementação concreta (`infrastructure/persistence/
gateways.py`) delega para os repositórios daquele contexto dentro da mesma
sessão/transação, o que garante a atomicidade Pedido+Estoque exigida pelo
caso de uso `criar_pedido`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from amactive.contexts.vendas.domain.entities import OrigemCanalPedido, Pedido, StatusPedido


@dataclass(frozen=True)
class VarianteVenda:
    """DTO somente-leitura com os dados de uma variante necessários para
    compor um item de venda (preço/SKU/ativo)."""

    id: UUID
    sku: str
    preco_venda: Decimal
    ativo: bool
    # Usados só pela vitrine (preço promocional e nome no pedido). Defaults
    # mantêm 100% de compatibilidade com o checkout do PDV/canais.
    produto_nome: str = ""
    desconto_percentual: Decimal | None = None


class CatalogoPort(Protocol):
    async def buscar_variante_para_venda(self, variante_id: UUID) -> VarianteVenda | None: ...


class EstoquePort(Protocol):
    async def registrar_saida_venda(
        self, *, variante_id: UUID, quantidade: int, pedido_id: UUID, usuario_id: UUID
    ) -> None: ...

    async def registrar_entrada_devolucao(
        self, *, variante_id: UUID, quantidade: int, pedido_id: UUID, usuario_id: UUID
    ) -> None: ...

    async def saldo_bloqueado(self, variante_id: UUID) -> int:
        """Saldo físico da variante, com `SELECT ... FOR UPDATE` na linha de
        `estoque` — serializa checkouts concorrentes da mesma variante até o
        fim da transação (ver docs/data-model.md § Concorrência)."""
        ...


class ClientePort(Protocol):
    async def obter_ou_criar_por_telefone(self, *, nome: str, telefone: str) -> UUID: ...


class ReservaEstoquePort(Protocol):
    async def quantidade_reservada_ativa(self, variante_id: UUID, *, agora: datetime) -> int: ...

    async def registrar(self, *, pedido_id: UUID, variante_id: UUID, quantidade: int) -> None: ...

    async def liberar_do_pedido(self, pedido_id: UUID) -> None: ...

    async def pedidos_com_reserva_vencida(self, *, agora: datetime) -> list[UUID]: ...


class PedidoRepository(Protocol):
    async def proximo_numero(self) -> str: ...

    async def criar(
        self,
        *,
        numero: str,
        cliente_id: UUID | None,
        usuario_id: UUID | None,
        status: StatusPedido,
        subtotal: Decimal,
        desconto: Decimal,
        valor_total: Decimal,
        observacao: str | None,
        confirmado_em: datetime | None,
        origem_canal: OrigemCanalPedido,
        pedido_externo_id: str | None,
        itens: list[dict],
        pagamentos: list[dict],
        reservado_ate: datetime | None = None,
    ) -> Pedido: ...

    async def adicionar_pagamentos(self, pedido_id: UUID, pagamentos: list[dict]) -> None: ...

    async def buscar_por_id(self, pedido_id: UUID) -> Pedido | None: ...

    async def existe_pedido_externo(
        self, *, origem_canal: OrigemCanalPedido, pedido_externo_id: str
    ) -> bool: ...

    async def listar(
        self,
        *,
        page: int,
        per_page: int,
        status: StatusPedido | None,
        cliente_id: UUID | None,
        data_inicio: date | None,
        data_fim: date | None,
        origem_canal: OrigemCanalPedido | None = None,
    ) -> tuple[list[Pedido], int]: ...

    async def atualizar_status(
        self, pedido_id: UUID, *, status: StatusPedido, timestamp: datetime
    ) -> None: ...
