"""Consultas de leitura da vitrine pública (read model).

Não passam por casos de uso nem por repositórios de escrita: são projeções
somente-leitura, como em `relatorios`. Só expõem o que o cliente final precisa
para escolher e pagar — nunca custo (`preco_custo`), fornecedor, estoque mínimo
ou dados de outros clientes.

Disponibilidade = saldo físico (`estoque.quantidade`) - reservas ativas, onde
reserva ativa é de um pedido PENDENTE com `reservado_ate` no futuro. Os mesmos
critérios são usados pelo checkout (`CriarPedidoVitrineUseCase`), então o que
aparece como disponível na vitrine é o que o checkout aceita.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import (
    CategoriaModel,
    EstoqueModel,
    ProdutoImagemModel,
    ProdutoModel,
    ProdutoVarianteModel,
)
from amactive.contexts.vendas.infrastructure.persistence.models import (
    PedidoModel,
    ReservaEstoqueModel,
)
from amactive.shared_kernel.money import aplicar_desconto_percentual
from amactive.shared_kernel.pagination import offset_limit


@dataclass(frozen=True)
class VarianteVitrine:
    id: UUID
    sku: str
    tamanho: str
    cor: str
    preco_unitario: Decimal  # já com desconto promocional, se houver
    preco_cheio: Decimal
    disponivel: int


@dataclass(frozen=True)
class ImagemVitrine:
    cor: str
    url: str
    principal: bool


@dataclass(frozen=True)
class ProdutoVitrine:
    id: UUID
    nome: str
    descricao: str | None
    marca: str
    categoria_id: UUID | None
    categoria_nome: str | None
    desconto_percentual: Decimal | None
    variantes: list[VarianteVitrine] = field(default_factory=list)
    imagens: list[ImagemVitrine] = field(default_factory=list)


@dataclass(frozen=True)
class CategoriaVitrine:
    id: UUID
    nome: str
    slug: str


def _subquery_reservado(agora: datetime):
    """Soma das unidades reservadas por variante, só de reservas vigentes."""
    return (
        select(
            ReservaEstoqueModel.variante_id.label("variante_id"),
            func.sum(ReservaEstoqueModel.quantidade).label("reservado"),
        )
        .join(PedidoModel, PedidoModel.id == ReservaEstoqueModel.pedido_id)
        .where(PedidoModel.status == "PENDENTE", PedidoModel.reservado_ate > agora)
        .group_by(ReservaEstoqueModel.variante_id)
        .subquery()
    )


def _preco_efetivo(preco: Decimal, desconto: Decimal | None) -> Decimal:
    if desconto is None:
        return preco
    return aplicar_desconto_percentual(preco, desconto)


async def listar_categorias(session: AsyncSession) -> list[CategoriaVitrine]:
    resultado = await session.execute(
        select(CategoriaModel.id, CategoriaModel.nome, CategoriaModel.slug)
        .where(CategoriaModel.ativo.is_(True))
        .order_by(CategoriaModel.nome)
    )
    return [CategoriaVitrine(id=i, nome=n, slug=s) for i, n, s in resultado.all()]


async def listar_produtos(
    session: AsyncSession,
    *,
    agora: datetime,
    page: int,
    per_page: int,
    categoria_id: UUID | None,
    busca: str | None,
) -> tuple[list[ProdutoVitrine], int]:
    """Produtos vendáveis: ativos, não excluídos e com pelo menos uma variante
    ativa. Variantes sem saldo aparecem com `disponivel=0` (o cliente vê que
    existe, mas não pode pedir)."""
    condicoes: list[ColumnElement[bool]] = [
        ProdutoModel.ativo.is_(True),
        ProdutoModel.deletado_em.is_(None),
        ProdutoVarianteModel.ativo.is_(True),
    ]
    if categoria_id is not None:
        condicoes.append(ProdutoModel.categoria_id == categoria_id)
    if busca:
        condicoes.append(ProdutoModel.nome.ilike(f"%{busca.strip()}%"))

    base = (
        select(ProdutoModel.id)
        .join(ProdutoVarianteModel, ProdutoVarianteModel.produto_id == ProdutoModel.id)
        .where(*condicoes)
        .group_by(ProdutoModel.id)
    )
    total = await session.scalar(select(func.count()).select_from(base.subquery()))

    offset, limit = offset_limit(page=page, per_page=per_page)
    ids_pagina = [
        pid
        for (pid,) in await session.execute(
            base.order_by(func.min(ProdutoModel.nome), ProdutoModel.id).offset(offset).limit(limit)
        )
    ]
    if not ids_pagina:
        return [], int(total or 0)

    produtos = await _carregar_produtos(session, ids_pagina, agora=agora)
    # Mantém a ordem da paginação (a consulta de carga não garante ordem).
    ordem = {pid: i for i, pid in enumerate(ids_pagina)}
    produtos.sort(key=lambda p: ordem[p.id])
    return produtos, int(total or 0)


async def obter_produto(
    session: AsyncSession, produto_id: UUID, *, agora: datetime
) -> ProdutoVitrine | None:
    condicoes = [
        ProdutoModel.id == produto_id,
        ProdutoModel.ativo.is_(True),
        ProdutoModel.deletado_em.is_(None),
    ]
    existe = await session.scalar(select(ProdutoModel.id).where(*condicoes))
    if existe is None:
        return None
    produtos = await _carregar_produtos(session, [produto_id], agora=agora)
    return produtos[0] if produtos else None


async def _carregar_produtos(
    session: AsyncSession, produto_ids: list[UUID], *, agora: datetime
) -> list[ProdutoVitrine]:
    reservado = _subquery_reservado(agora)

    produtos_resultado = await session.execute(
        select(
            ProdutoModel.id,
            ProdutoModel.nome,
            ProdutoModel.descricao,
            ProdutoModel.marca,
            ProdutoModel.categoria_id,
            CategoriaModel.nome.label("categoria_nome"),
            ProdutoModel.desconto_percentual,
        )
        .outerjoin(CategoriaModel, CategoriaModel.id == ProdutoModel.categoria_id)
        .where(ProdutoModel.id.in_(produto_ids))
    )
    produtos: dict[UUID, ProdutoVitrine] = {
        linha.id: ProdutoVitrine(
            id=linha.id,
            nome=linha.nome,
            descricao=linha.descricao,
            marca=linha.marca,
            categoria_id=linha.categoria_id,
            categoria_nome=linha.categoria_nome,
            desconto_percentual=linha.desconto_percentual,
        )
        for linha in produtos_resultado.all()
    }

    variantes_resultado = await session.execute(
        select(
            ProdutoVarianteModel.produto_id,
            ProdutoVarianteModel.id,
            ProdutoVarianteModel.sku,
            ProdutoVarianteModel.tamanho,
            ProdutoVarianteModel.cor,
            ProdutoVarianteModel.preco_venda,
            (EstoqueModel.quantidade - func.coalesce(reservado.c.reservado, 0)).label("disponivel"),
        )
        .join(EstoqueModel, EstoqueModel.variante_id == ProdutoVarianteModel.id)
        .outerjoin(reservado, reservado.c.variante_id == ProdutoVarianteModel.id)
        .where(
            ProdutoVarianteModel.produto_id.in_(produto_ids),
            ProdutoVarianteModel.ativo.is_(True),
        )
        .order_by(ProdutoVarianteModel.cor, ProdutoVarianteModel.tamanho)
    )
    for linha in variantes_resultado.all():
        produto = produtos.get(linha.produto_id)
        if produto is None:
            continue
        preco_cheio = linha.preco_venda
        produto.variantes.append(
            VarianteVitrine(
                id=linha.id,
                sku=linha.sku,
                tamanho=linha.tamanho,
                cor=linha.cor,
                preco_unitario=_preco_efetivo(preco_cheio, produto.desconto_percentual),
                preco_cheio=preco_cheio,
                # Nunca negativo, mesmo se uma reserva antiga superar o saldo.
                disponivel=max(int(linha.disponivel or 0), 0),
            )
        )

    imagens_resultado = await session.execute(
        select(
            ProdutoImagemModel.produto_id,
            ProdutoImagemModel.cor,
            ProdutoImagemModel.url,
            ProdutoImagemModel.principal,
        )
        .where(ProdutoImagemModel.produto_id.in_(produto_ids))
        .order_by(ProdutoImagemModel.cor, ProdutoImagemModel.ordem)
    )
    for imagem in imagens_resultado.all():
        produto = produtos.get(imagem.produto_id)
        if produto is not None:
            produto.imagens.append(
                ImagemVitrine(cor=imagem.cor, url=imagem.url, principal=imagem.principal)
            )

    # Produto sem nenhuma variante ativa não é vendável: some da listagem.
    return [p for p in produtos.values() if p.variantes]


async def descrever_variantes(session: AsyncSession, variante_ids: list[UUID]) -> dict[UUID, str]:
    """Nome legível de cada variante (para a mensagem de WhatsApp do pedido)."""
    resultado = await session.execute(
        select(
            ProdutoVarianteModel.id,
            ProdutoModel.nome,
            ProdutoVarianteModel.cor,
            ProdutoVarianteModel.tamanho,
        )
        .join(ProdutoModel, ProdutoModel.id == ProdutoVarianteModel.produto_id)
        .where(ProdutoVarianteModel.id.in_(variante_ids))
    )
    return {vid: f"{nome} {cor} {tamanho}".strip() for vid, nome, cor, tamanho in resultado.all()}
