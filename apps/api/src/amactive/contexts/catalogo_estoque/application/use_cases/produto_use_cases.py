"""Casos de uso de Produto (Command/Query)."""

from __future__ import annotations

from uuid import UUID

from amactive.contexts.catalogo_estoque.domain.entities import Produto
from amactive.contexts.catalogo_estoque.domain.exceptions import ProdutoNaoEncontrado
from amactive.contexts.catalogo_estoque.domain.repositories import ProdutoRepository


class CriarProdutoCommand:
    def __init__(self, repository: ProdutoRepository) -> None:
        self._repository = repository

    async def executar(
        self, *, nome: str, descricao: str | None, categoria_id: UUID | None, marca: str
    ) -> Produto:
        return await self._repository.criar(
            nome=nome, descricao=descricao, categoria_id=categoria_id, marca=marca
        )


class ListarProdutosQuery:
    def __init__(self, repository: ProdutoRepository) -> None:
        self._repository = repository

    async def executar(
        self,
        *,
        page: int,
        per_page: int,
        busca: str | None,
        categoria_id: UUID | None,
        ativo: bool | None,
    ) -> tuple[list[Produto], int]:
        return await self._repository.listar(
            page=page, per_page=per_page, busca=busca, categoria_id=categoria_id, ativo=ativo
        )


class ObterProdutoQuery:
    def __init__(self, repository: ProdutoRepository) -> None:
        self._repository = repository

    async def executar(self, produto_id: UUID) -> Produto:
        produto = await self._repository.buscar_por_id(produto_id)
        if produto is None:
            raise ProdutoNaoEncontrado(f"Produto {produto_id} não encontrado.")
        return produto


class AtualizarProdutoCommand:
    def __init__(self, repository: ProdutoRepository) -> None:
        self._repository = repository

    async def executar(self, produto_id: UUID, **campos: object) -> Produto:
        produto = await self._repository.atualizar(produto_id, **campos)
        if produto is None:
            raise ProdutoNaoEncontrado(f"Produto {produto_id} não encontrado.")
        return produto


class InativarProdutoCommand:
    def __init__(self, repository: ProdutoRepository) -> None:
        self._repository = repository

    async def executar(self, produto_id: UUID) -> None:
        inativado = await self._repository.inativar(produto_id)
        if not inativado:
            raise ProdutoNaoEncontrado(f"Produto {produto_id} não encontrado.")
