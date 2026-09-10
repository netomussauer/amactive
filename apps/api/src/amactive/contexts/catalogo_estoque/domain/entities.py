"""Entidades do contexto Catálogo & Estoque — ver docs/data-model.md."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


class TipoMovimentacao(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"
    AJUSTE = "AJUSTE"


class MotivoMovimentacao(str, Enum):
    COMPRA = "COMPRA"
    VENDA = "VENDA"
    AJUSTE_INVENTARIO = "AJUSTE_INVENTARIO"
    DEVOLUCAO = "DEVOLUCAO"
    PERDA = "PERDA"


@dataclass(frozen=True)
class Categoria:
    id: UUID
    nome: str
    slug: str
    ativo: bool


@dataclass(frozen=True)
class Produto:
    id: UUID
    nome: str
    descricao: str | None
    categoria_id: UUID | None
    marca: str
    ativo: bool
    criado_em: datetime


@dataclass(frozen=True)
class ProdutoVariante:
    id: UUID
    produto_id: UUID
    sku: str
    tamanho: str
    cor: str
    preco_venda: Decimal
    preco_custo: Decimal | None
    ativo: bool


@dataclass(frozen=True)
class Estoque:
    variante_id: UUID
    sku: str
    produto_nome: str
    quantidade: int
    estoque_minimo: int

    @property
    def em_alerta(self) -> bool:
        return self.quantidade <= self.estoque_minimo


@dataclass(frozen=True)
class MovimentacaoEstoque:
    id: UUID
    variante_id: UUID
    sku: str
    tipo: TipoMovimentacao
    quantidade: int
    motivo: MotivoMovimentacao
    pedido_id: UUID | None
    fornecedor_id: UUID | None
    usuario_id: UUID
    criado_em: datetime
