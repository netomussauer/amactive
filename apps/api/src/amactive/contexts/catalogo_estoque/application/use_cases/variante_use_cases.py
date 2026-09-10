"""Casos de uso de Variante (SKU) — Command/Query."""

from __future__ import annotations

import re
from decimal import Decimal
from uuid import UUID, uuid4

from amactive.contexts.catalogo_estoque.domain.entities import (
    MotivoMovimentacao,
    ProdutoVariante,
    TipoMovimentacao,
)
from amactive.contexts.catalogo_estoque.domain.exceptions import VarianteNaoEncontrada
from amactive.contexts.catalogo_estoque.domain.repositories import (
    MovimentacaoRepository,
    VarianteRepository,
)


def gerar_sku(*, tamanho: str, cor: str) -> str:
    """Gera um SKU legível e praticamente único quando o cliente não informa um."""
    cor_slug = re.sub(r"[^A-Z0-9]+", "", cor.upper())[:6] or "COR"
    tamanho_slug = re.sub(r"[^A-Z0-9]+", "", tamanho.upper())[:4] or "UN"
    return f"SKU-{tamanho_slug}-{cor_slug}-{uuid4().hex[:6].upper()}"


class CriarVarianteCommand:
    """Cria a variante e, se `estoque_inicial > 0`, registra a movimentação de
    entrada correspondente (o saldo zerado em `estoque` já é criado
    automaticamente por trigger de banco — ver docs/data-model.md decisão #11)."""

    def __init__(
        self,
        variante_repository: VarianteRepository,
        movimentacao_repository: MovimentacaoRepository,
    ) -> None:
        self._variantes = variante_repository
        self._movimentacoes = movimentacao_repository

    async def executar(
        self,
        *,
        produto_id: UUID,
        sku: str | None,
        tamanho: str,
        cor: str,
        preco_venda: Decimal,
        preco_custo: Decimal | None,
        estoque_inicial: int,
        usuario_id: UUID,
    ) -> ProdutoVariante:
        sku_final = sku or gerar_sku(tamanho=tamanho, cor=cor)
        variante = await self._variantes.criar(
            produto_id=produto_id,
            sku=sku_final,
            tamanho=tamanho,
            cor=cor,
            preco_venda=preco_venda,
            preco_custo=preco_custo,
        )
        if estoque_inicial > 0:
            await self._movimentacoes.registrar(
                variante_id=variante.id,
                tipo=TipoMovimentacao.ENTRADA,
                quantidade=estoque_inicial,
                motivo=MotivoMovimentacao.AJUSTE_INVENTARIO,
                usuario_id=usuario_id,
            )
        return variante


class ListarVariantesDoProdutoQuery:
    def __init__(self, repository: VarianteRepository) -> None:
        self._repository = repository

    async def executar(self, produto_id: UUID) -> list[ProdutoVariante]:
        return await self._repository.listar_por_produto(produto_id)


class ObterVarianteQuery:
    def __init__(self, repository: VarianteRepository) -> None:
        self._repository = repository

    async def executar(self, variante_id: UUID) -> ProdutoVariante:
        variante = await self._repository.buscar_por_id(variante_id)
        if variante is None:
            raise VarianteNaoEncontrada(f"Variante {variante_id} não encontrada.")
        return variante


class AtualizarVarianteCommand:
    def __init__(self, repository: VarianteRepository) -> None:
        self._repository = repository

    async def executar(self, variante_id: UUID, **campos: object) -> ProdutoVariante:
        variante = await self._repository.atualizar(variante_id, **campos)
        if variante is None:
            raise VarianteNaoEncontrada(f"Variante {variante_id} não encontrada.")
        return variante


class InativarVarianteCommand:
    def __init__(self, repository: VarianteRepository) -> None:
        self._repository = repository

    async def executar(self, variante_id: UUID) -> None:
        inativada = await self._repository.inativar(variante_id)
        if not inativada:
            raise VarianteNaoEncontrada(f"Variante {variante_id} não encontrada.")
