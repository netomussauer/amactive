"""Schemas HTTP (Pydantic) — espelham docs/openapi.yaml (Categorias, Produtos,
Variantes, Estoque)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from amactive.contexts.catalogo_estoque.domain.entities import MotivoMovimentacao, TipoMovimentacao
from amactive.shared_kernel.schemas import Pagination

MoneyStr = str  # padrão '^\d+\.\d{2}$', validado/formatado via amactive.shared_kernel.money


# ── Categorias ──
class CriarCategoriaRequest(BaseModel):
    nome: str = Field(max_length=100)


class CategoriaResponse(BaseModel):
    id: UUID
    nome: str
    slug: str
    ativo: bool


class CategoriaListResponse(BaseModel):
    data: list[CategoriaResponse]


# ── Produtos ──
class CriarProdutoRequest(BaseModel):
    nome: str = Field(max_length=200)
    descricao: str | None = None
    categoria_id: UUID | None = None
    marca: str = "AMACTIVE"


class AtualizarProdutoRequest(CriarProdutoRequest):
    ativo: bool | None = None


class ProdutoResponse(BaseModel):
    id: UUID
    nome: str
    descricao: str | None
    categoria_id: UUID | None
    marca: str
    ativo: bool
    criado_em: datetime


class VarianteResponse(BaseModel):
    id: UUID
    produto_id: UUID
    sku: str
    tamanho: str
    cor: str
    preco_venda: MoneyStr
    preco_custo: MoneyStr | None
    ativo: bool
    quantidade_estoque: int


class ProdutoDetalheResponse(ProdutoResponse):
    variantes: list[VarianteResponse] = Field(default_factory=list)


class ProdutoListResponse(BaseModel):
    data: list[ProdutoResponse]
    pagination: Pagination


# ── Variantes ──
class CriarVarianteRequest(BaseModel):
    sku: str | None = None
    tamanho: str
    cor: str = Field(max_length=50)
    preco_venda: str = Field(pattern=r"^\d+\.\d{2}$")
    preco_custo: str | None = Field(default=None, pattern=r"^\d+\.\d{2}$")
    estoque_inicial: int = Field(default=0, ge=0)


class AtualizarVarianteRequest(BaseModel):
    cor: str | None = None
    preco_venda: str | None = Field(default=None, pattern=r"^\d+\.\d{2}$")
    preco_custo: str | None = Field(default=None, pattern=r"^\d+\.\d{2}$")
    ativo: bool | None = None


class VarianteListResponse(BaseModel):
    data: list[VarianteResponse]


# ── Estoque ──
class EstoqueResponse(BaseModel):
    variante_id: UUID
    sku: str
    produto_nome: str
    quantidade: int
    estoque_minimo: int
    em_alerta: bool


class EstoqueListResponse(BaseModel):
    data: list[EstoqueResponse]
    pagination: Pagination


class EstoqueAlertaListResponse(BaseModel):
    data: list[EstoqueResponse]


class CriarMovimentacaoRequest(BaseModel):
    variante_id: UUID
    tipo: TipoMovimentacao
    quantidade: int = Field(ge=1)
    motivo: MotivoMovimentacao
    fornecedor_id: UUID | None = None


class MovimentacaoResponse(BaseModel):
    id: UUID
    variante_id: UUID
    sku: str
    tipo: str
    quantidade: int
    motivo: str
    pedido_id: UUID | None
    fornecedor_id: UUID | None
    usuario_id: UUID
    criado_em: datetime


class MovimentacaoListResponse(BaseModel):
    data: list[MovimentacaoResponse]
    pagination: Pagination
