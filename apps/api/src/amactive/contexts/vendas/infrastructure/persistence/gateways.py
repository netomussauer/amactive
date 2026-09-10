"""Adaptador do Shared Kernel restrito (ver docs/SDD.md §1.2 e
domain/repositories.py deste contexto): implementa `CatalogoPort`/
`EstoquePort` delegando para os repositórios concretos de Catálogo &
Estoque, sempre na MESMA sessão/transação — é assim que a atomicidade
Pedido+Estoque é garantida sem Vendas acoplar-se às tabelas físicas de
outro contexto.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.domain.entities import (
    MotivoMovimentacao,
    TipoMovimentacao,
)
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyMovimentacaoRepository,
    SqlAlchemyVarianteRepository,
)
from amactive.contexts.vendas.domain.repositories import VarianteVenda


class CatalogoEstoqueGateway:
    """Implementa, em uma única classe, os dois Protocols publicados por
    Catálogo & Estoque (`CatalogoPort` e `EstoquePort`) que o contexto de
    Vendas consome."""

    def __init__(self, session: AsyncSession) -> None:
        self._variantes = SqlAlchemyVarianteRepository(session)
        self._movimentacoes = SqlAlchemyMovimentacaoRepository(session)

    async def buscar_variante_para_venda(self, variante_id: UUID) -> VarianteVenda | None:
        variante = await self._variantes.buscar_por_id(variante_id)
        if variante is None:
            return None
        return VarianteVenda(
            id=variante.id,
            sku=variante.sku,
            preco_venda=variante.preco_venda,
            ativo=variante.ativo,
        )

    async def registrar_saida_venda(
        self, *, variante_id: UUID, quantidade: int, pedido_id: UUID, usuario_id: UUID
    ) -> None:
        await self._movimentacoes.registrar(
            variante_id=variante_id,
            tipo=TipoMovimentacao.SAIDA,
            quantidade=quantidade,
            motivo=MotivoMovimentacao.VENDA,
            usuario_id=usuario_id,
            pedido_id=pedido_id,
        )

    async def registrar_entrada_devolucao(
        self, *, variante_id: UUID, quantidade: int, pedido_id: UUID, usuario_id: UUID
    ) -> None:
        await self._movimentacoes.registrar(
            variante_id=variante_id,
            tipo=TipoMovimentacao.ENTRADA,
            quantidade=quantidade,
            motivo=MotivoMovimentacao.DEVOLUCAO,
            usuario_id=usuario_id,
            pedido_id=pedido_id,
        )
