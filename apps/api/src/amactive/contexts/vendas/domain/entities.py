"""Entidades do contexto Vendas — ver docs/data-model.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


class StatusPedido(str, Enum):
    PENDENTE = "PENDENTE"
    CONFIRMADO = "CONFIRMADO"
    CANCELADO = "CANCELADO"


class FormaPagamento(str, Enum):
    DINHEIRO = "DINHEIRO"
    PIX = "PIX"
    CARTAO_DEBITO = "CARTAO_DEBITO"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    # Pago externamente via checkout do canal (ex.: Nuvemshop) — detalhamento
    # por método (PIX/cartão específico do comprador) não é replicado no MVP.
    # Ver docs/design-integracao-nuvemshop.md §3.1.
    NUVEMSHOP = "NUVEMSHOP"


class OrigemCanalPedido(str, Enum):
    """Canal de origem do pedido — ver docs/design-integracao-nuvemshop.md
    §2.3 (nota de Ubiquitous Language: vocabulário de `vendas`, distinto de
    `CanalIntegracao` de `integracao_canais`)."""

    PDV = "PDV"
    NUVEMSHOP = "NUVEMSHOP"
    # migrations/000006_origem_canal_whatsapp — pedidos registrados
    # manualmente a partir de vendas fechadas por WhatsApp.
    WHATSAPP = "WHATSAPP"
    # migrations/000007_origem_canal_vitrine — pedido feito pelo cliente final
    # na loja online; sem operador, aguarda confirmação de pagamento.
    VITRINE = "VITRINE"


@dataclass(frozen=True)
class ItemPedido:
    id: UUID
    variante_id: UUID
    sku: str
    quantidade: int
    preco_unitario: Decimal
    desconto_item: Decimal
    subtotal: Decimal


@dataclass(frozen=True)
class PagamentoPedido:
    id: UUID
    forma_pagamento: FormaPagamento
    valor: Decimal


@dataclass(frozen=True)
class Pedido:
    id: UUID
    numero: str
    cliente_id: UUID | None
    # None apenas para pedidos da VITRINE (cliente final, sem operador) —
    # ver CHECK chk_pedido_usuario_obrigatorio em migrations/000008.
    usuario_id: UUID | None
    status: StatusPedido
    subtotal: Decimal
    desconto: Decimal
    valor_total: Decimal
    observacao: str | None
    criado_em: datetime
    confirmado_em: datetime | None
    cancelado_em: datetime | None
    origem_canal: OrigemCanalPedido
    pedido_externo_id: str | None
    # Prazo da reserva de estoque de um pedido PENDENTE da vitrine (migrations/000008).
    reservado_ate: datetime | None = None
    itens: list[ItemPedido] = field(default_factory=list)
    pagamentos: list[PagamentoPedido] = field(default_factory=list)
