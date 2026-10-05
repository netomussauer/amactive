"""Adaptador do Shared Kernel restrito (ver docs/SDD.md §1.2 e
domain/repositories.py deste contexto): implementa `CatalogoPort`/
`EstoquePort` delegando para os repositórios concretos de Catálogo &
Estoque, sempre na MESMA sessão/transação — é assim que a atomicidade
Pedido+Estoque é garantida sem Vendas acoplar-se às tabelas físicas de
outro contexto.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.cadastros.infrastructure.persistence.models import ClienteModel
from amactive.contexts.catalogo_estoque.domain.entities import (
    MotivoMovimentacao,
    TipoMovimentacao,
)
from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import (
    EstoqueModel,
    ProdutoModel,
    ProdutoVarianteModel,
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
        self._session = session
        self._variantes = SqlAlchemyVarianteRepository(session)
        self._movimentacoes = SqlAlchemyMovimentacaoRepository(session)

    async def buscar_variante_para_venda(self, variante_id: UUID) -> VarianteVenda | None:
        variante = await self._variantes.buscar_por_id(variante_id)
        if variante is None:
            return None
        # Nome e desconto do produto: só a vitrine os usa, mas são lidos na
        # mesma linha de catálogo para não multiplicar consultas no checkout.
        resultado = await self._session.execute(
            select(ProdutoModel.nome, ProdutoModel.desconto_percentual)
            .join(ProdutoVarianteModel, ProdutoVarianteModel.produto_id == ProdutoModel.id)
            .where(ProdutoVarianteModel.id == variante_id)
        )
        linha = resultado.first()
        return VarianteVenda(
            id=variante.id,
            sku=variante.sku,
            preco_venda=variante.preco_venda,
            ativo=variante.ativo,
            produto_nome=linha.nome if linha else "",
            desconto_percentual=linha.desconto_percentual if linha else None,
        )

    async def saldo_bloqueado(self, variante_id: UUID) -> int:
        quantidade = await self._session.scalar(
            select(EstoqueModel.quantidade)
            .where(EstoqueModel.variante_id == variante_id)
            .with_for_update()
        )
        return int(quantidade or 0)

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


class ClienteCadastrosGateway:
    """Implementa `ClientePort` lendo/gravando a tabela `cliente` do contexto
    de Cadastros. Para a vitrine, o cliente é identificado pelo telefone
    (só dígitos) — o cliente final não informa CPF nem e-mail."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obter_ou_criar_por_telefone(self, *, nome: str, telefone: str) -> UUID:
        digitos = re.sub(r"\D", "", telefone)
        existente = await self._session.scalar(
            select(ClienteModel.id)
            .where(ClienteModel.telefone == digitos, ClienteModel.ativo.is_(True))
            .order_by(ClienteModel.criado_em)
            .limit(1)
        )
        if existente is not None:
            return existente
        novo = ClienteModel(
            id=uuid4(),
            nome=nome.strip(),
            telefone=digitos,
            ativo=True,
            criado_em=datetime.now(UTC),
        )
        self._session.add(novo)
        await self._session.flush()
        return novo.id
