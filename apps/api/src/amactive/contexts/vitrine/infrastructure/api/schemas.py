"""Schemas HTTP da vitrine pública. Propositalmente enxutos: nenhum campo de
custo, fornecedor, estoque mínimo ou dado de outro cliente."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from amactive.shared_kernel.schemas import Pagination

NomeCliente = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
TelefoneCliente = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=10, max_length=20)
]


class CategoriaPublica(BaseModel):
    id: UUID
    nome: str
    slug: str


class CategoriaRefPublica(BaseModel):
    id: UUID
    nome: str


class VariantePublica(BaseModel):
    id: UUID
    sku: str
    tamanho: str
    cor: str
    preco_unitario: str
    preco_cheio: str
    disponivel: int


class ImagemPublica(BaseModel):
    cor: str
    url: str
    principal: bool


class ProdutoResumoPublico(BaseModel):
    id: UUID
    nome: str
    marca: str
    categoria: CategoriaRefPublica | None
    desconto_percentual: str | None
    preco_a_partir_de: str
    imagem_principal_url: str | None
    cores: list[str]


class ProdutoListaPublica(BaseModel):
    data: list[ProdutoResumoPublico]
    pagination: Pagination


class ProdutoDetalhePublico(ProdutoResumoPublico):
    descricao: str | None
    variantes: list[VariantePublica]
    imagens: list[ImagemPublica]


class ItemCheckoutRequest(BaseModel):
    variante_id: UUID
    quantidade: int = Field(ge=1, le=20)


class ClienteCheckoutRequest(BaseModel):
    nome: NomeCliente
    telefone: TelefoneCliente


class CheckoutRequest(BaseModel):
    cliente: ClienteCheckoutRequest
    observacao: str | None = Field(default=None, max_length=500)
    itens: list[ItemCheckoutRequest] = Field(min_length=1, max_length=30)


class ItemPedidoPublico(BaseModel):
    sku: str
    descricao: str
    quantidade: int
    preco_unitario: str
    subtotal: str


class PedidoCheckoutPublico(BaseModel):
    numero: str
    status: str
    subtotal: str
    valor_total: str
    reservado_ate: datetime
    itens: list[ItemPedidoPublico]
