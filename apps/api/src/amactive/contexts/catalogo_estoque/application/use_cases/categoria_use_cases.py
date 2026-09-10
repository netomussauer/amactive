"""Casos de uso de Categoria (Command/Query)."""

from __future__ import annotations

import re
import unicodedata

from amactive.contexts.catalogo_estoque.domain.entities import Categoria
from amactive.contexts.catalogo_estoque.domain.repositories import CategoriaRepository


def slugify(texto: str) -> str:
    """Gera um slug ASCII/kebab-case a partir de um nome livre."""
    normalizado = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalizado).strip("-").lower()
    return slug or "categoria"


class ListarCategoriasQuery:
    def __init__(self, repository: CategoriaRepository) -> None:
        self._repository = repository

    async def executar(self) -> list[Categoria]:
        return await self._repository.listar()


class CriarCategoriaCommand:
    def __init__(self, repository: CategoriaRepository) -> None:
        self._repository = repository

    async def executar(self, *, nome: str) -> Categoria:
        return await self._repository.criar(nome=nome, slug=slugify(nome))
