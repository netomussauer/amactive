"""Portas (Protocols) do contexto Catálogo & Estoque.

`MovimentacaoRepository` é também o **EstoquePort** publicado para o
contexto de Vendas (Shared Kernel restrito — ver docs/SDD.md §1.2): Vendas
conhece apenas este Protocol, nunca a tabela `movimentacao_estoque`
diretamente.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Protocol
from uuid import UUID

from amactive.contexts.catalogo_estoque.domain.entities import (
    Categoria,
    Estoque,
    MotivoMovimentacao,
    MovimentacaoEstoque,
    Produto,
    ProdutoVariante,
    TipoMovimentacao,
)


class CategoriaRepository(Protocol):
    async def listar(self) -> list[Categoria]: ...

    async def criar(self, *, nome: str, slug: str) -> Categoria: ...


class ProdutoRepository(Protocol):
    async def criar(
        self, *, nome: str, descricao: str | None, categoria_id: UUID | None, marca: str
    ) -> Produto: ...

    async def listar(
        self,
        *,
        page: int,
        per_page: int,
        busca: str | None,
        categoria_id: UUID | None,
        ativo: bool | None,
    ) -> tuple[list[Produto], int]: ...

    async def buscar_por_id(self, produto_id: UUID) -> Produto | None: ...

    async def atualizar(self, produto_id: UUID, **campos: object) -> Produto | None: ...

    async def inativar(self, produto_id: UUID) -> bool: ...


class VarianteRepository(Protocol):
    async def criar(
        self,
        *,
        produto_id: UUID,
        sku: str,
        tamanho: str,
        cor: str,
        preco_venda: Decimal,
        preco_custo: Decimal | None,
    ) -> ProdutoVariante: ...

    async def listar_por_produto(self, produto_id: UUID) -> list[ProdutoVariante]: ...

    async def buscar_por_id(self, variante_id: UUID) -> ProdutoVariante | None: ...

    async def atualizar(self, variante_id: UUID, **campos: object) -> ProdutoVariante | None: ...

    async def inativar(self, variante_id: UUID) -> bool: ...


class EstoqueRepository(Protocol):
    async def listar(
        self, *, page: int, per_page: int, sku: str | None
    ) -> tuple[list[Estoque], int]: ...

    async def listar_em_alerta(self) -> list[Estoque]: ...

    async def buscar_por_variante(self, variante_id: UUID) -> Estoque | None: ...


class MovimentacaoRepository(Protocol):
    async def registrar(
        self,
        *,
        variante_id: UUID,
        tipo: TipoMovimentacao,
        quantidade: int,
        motivo: MotivoMovimentacao,
        usuario_id: UUID,
        pedido_id: UUID | None = None,
        fornecedor_id: UUID | None = None,
    ) -> MovimentacaoEstoque: ...

    async def listar(
        self,
        *,
        page: int,
        per_page: int,
        variante_id: UUID | None,
        tipo: TipoMovimentacao | None,
    ) -> tuple[list[MovimentacaoEstoque], int]: ...
