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


class CatalogoPort(Protocol):
    async def buscar_variante_para_venda(self, variante_id: UUID) -> VarianteVenda | None: ...


class EstoquePort(Protocol):
    async def registrar_saida_venda(
        self, *, variante_id: UUID, quantidade: int, pedido_id: UUID, usuario_id: UUID
    ) -> None: ...

    async def registrar_entrada_devolucao(
        self, *, variante_id: UUID, quantidade: int, pedido_id: UUID, usuario_id: UUID
    ) -> None: ...


class PedidoRepository(Protocol):
    async def proximo_numero(self) -> str: ...

    async def criar(
        self,
        *,
        numero: str,
        cliente_id: UUID | None,
        usuario_id: UUID,
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
    ) -> Pedido: ...

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
