"""Implementações concretas dos Protocols de `domain/repositories.py`
(Catálogo & Estoque), usando SQLAlchemy 2.x async (asyncpg)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.domain.entities import (
    Categoria,
    Estoque,
    MotivoMovimentacao,
    MovimentacaoEstoque,
    Produto,
    ProdutoImagem,
    ProdutoVariante,
    TipoMovimentacao,
)
from amactive.contexts.catalogo_estoque.domain.exceptions import (
    SaldoDeEstoqueInsuficiente,
    SkuDuplicado,
)
from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import (
    CategoriaModel,
    EstoqueModel,
    MovimentacaoEstoqueModel,
    ProdutoImagemModel,
    ProdutoModel,
    ProdutoVarianteModel,
)
from amactive.shared_kernel.exceptions import ConflitoTransacional
from amactive.shared_kernel.pagination import offset_limit

_SQLSTATE_SALDO_INSUFICIENTE = "P0001"
_SQLSTATE_DEADLOCK = "40P01"


def _now() -> datetime:
    return datetime.now(UTC)


class SqlAlchemyCategoriaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def listar(self) -> list[Categoria]:
        resultado = await self._session.execute(
            select(CategoriaModel).order_by(CategoriaModel.nome)
        )
        return [_categoria_para_entidade(m) for m in resultado.scalars().all()]

    async def criar(self, *, nome: str, slug: str) -> Categoria:
        modelo = CategoriaModel(id=uuid.uuid4(), nome=nome, slug=slug, ativo=True, criado_em=_now())
        self._session.add(modelo)
        await self._session.flush()
        return _categoria_para_entidade(modelo)


class SqlAlchemyProdutoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self, *, nome: str, descricao: str | None, categoria_id: UUID | None, marca: str
    ) -> Produto:
        modelo = ProdutoModel(
            id=uuid.uuid4(),
            nome=nome,
            descricao=descricao,
            categoria_id=categoria_id,
            marca=marca,
            ativo=True,
            criado_em=_now(),
        )
        self._session.add(modelo)
        await self._session.flush()
        return _produto_para_entidade(modelo)

    async def listar(
        self,
        *,
        page: int,
        per_page: int,
        busca: str | None,
        categoria_id: UUID | None,
        ativo: bool | None,
    ) -> tuple[list[Produto], int]:
        offset, limit = offset_limit(page=page, per_page=per_page)
        condicoes: list[ColumnElement[bool]] = [ProdutoModel.deletado_em.is_(None)]
        if busca:
            condicoes.append(ProdutoModel.nome.ilike(f"%{busca}%"))
        if categoria_id is not None:
            condicoes.append(ProdutoModel.categoria_id == categoria_id)
        if ativo is not None:
            condicoes.append(ProdutoModel.ativo == ativo)

        total = await self._session.scalar(
            select(func.count()).select_from(ProdutoModel).where(*condicoes)
        )
        resultado = await self._session.execute(
            select(ProdutoModel)
            .where(*condicoes)
            .order_by(ProdutoModel.nome)
            .offset(offset)
            .limit(limit)
        )
        produtos = [_produto_para_entidade(m) for m in resultado.scalars().all()]
        return produtos, int(total or 0)

    async def buscar_por_id(self, produto_id: UUID) -> Produto | None:
        modelo = await self._session.get(ProdutoModel, produto_id)
        return _produto_para_entidade(modelo) if modelo else None

    async def atualizar(self, produto_id: UUID, **campos: object) -> Produto | None:
        modelo = await self._session.get(ProdutoModel, produto_id)
        if modelo is None:
            return None
        for chave, valor in campos.items():
            if valor is not None or chave in {"descricao", "categoria_id"}:
                setattr(modelo, chave, valor)
        await self._session.flush()
        return _produto_para_entidade(modelo)

    async def inativar(self, produto_id: UUID) -> bool:
        modelo = await self._session.get(ProdutoModel, produto_id)
        if modelo is None:
            return False
        modelo.ativo = False
        await self._session.flush()
        return True


class SqlAlchemyVarianteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self,
        *,
        produto_id: UUID,
        sku: str,
        tamanho: str,
        cor: str,
        preco_venda: Decimal,
        preco_custo: Decimal | None,
    ) -> ProdutoVariante:
        modelo = ProdutoVarianteModel(
            id=uuid.uuid4(),
            produto_id=produto_id,
            sku=sku,
            tamanho=tamanho,
            cor=cor,
            preco_venda=preco_venda,
            preco_custo=preco_custo,
            ativo=True,
            criado_em=_now(),
        )
        self._session.add(modelo)
        try:
            await self._session.flush()
        except IntegrityError as exc:
            await self._session.rollback()
            raise SkuDuplicado(f"SKU '{sku}' já está em uso por outra variante.") from exc
        return _variante_para_entidade(modelo)

    async def listar_por_produto(self, produto_id: UUID) -> list[ProdutoVariante]:
        resultado = await self._session.execute(
            select(ProdutoVarianteModel)
            .where(ProdutoVarianteModel.produto_id == produto_id)
            .order_by(ProdutoVarianteModel.tamanho, ProdutoVarianteModel.cor)
        )
        return [_variante_para_entidade(m) for m in resultado.scalars().all()]

    async def buscar_por_id(self, variante_id: UUID) -> ProdutoVariante | None:
        modelo = await self._session.get(ProdutoVarianteModel, variante_id)
        return _variante_para_entidade(modelo) if modelo else None

    async def atualizar(self, variante_id: UUID, **campos: object) -> ProdutoVariante | None:
        modelo = await self._session.get(ProdutoVarianteModel, variante_id)
        if modelo is None:
            return None
        for chave, valor in campos.items():
            if valor is not None:
                setattr(modelo, chave, valor)
        await self._session.flush()
        return _variante_para_entidade(modelo)

    async def inativar(self, variante_id: UUID) -> bool:
        modelo = await self._session.get(ProdutoVarianteModel, variante_id)
        if modelo is None:
            return False
        modelo.ativo = False
        await self._session.flush()
        return True


class SqlAlchemyImagemRepository:
    """Implementação de `ImagemRepository`. Todos os métodos que recebem
    `produto_id`+`imagem_id` verificam que a imagem pertence de fato àquele
    produto antes de agir — devolvem `None` (404 na camada de aplicação)
    caso contrário, para nunca permitir manipular a imagem de um produto
    através da URL de outro."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(
        self, *, produto_id: UUID, cor: str, url: str, ordem: int, principal: bool
    ) -> ProdutoImagem:
        modelo = ProdutoImagemModel(
            id=uuid.uuid4(),
            produto_id=produto_id,
            cor=cor,
            url=url,
            ordem=ordem,
            principal=principal,
            criado_em=_now(),
        )
        self._session.add(modelo)
        await self._session.flush()
        return _imagem_para_entidade(modelo)

    async def listar_por_produto(
        self, produto_id: UUID, *, cor: str | None = None
    ) -> list[ProdutoImagem]:
        condicoes: list[ColumnElement[bool]] = [ProdutoImagemModel.produto_id == produto_id]
        if cor:
            condicoes.append(ProdutoImagemModel.cor == cor)
        resultado = await self._session.execute(
            select(ProdutoImagemModel)
            .where(*condicoes)
            .order_by(ProdutoImagemModel.cor, ProdutoImagemModel.ordem)
        )
        return [_imagem_para_entidade(m) for m in resultado.scalars().all()]

    async def buscar_por_id(self, produto_id: UUID, imagem_id: UUID) -> ProdutoImagem | None:
        modelo = await self._session.get(ProdutoImagemModel, imagem_id)
        if modelo is None or modelo.produto_id != produto_id:
            return None
        return _imagem_para_entidade(modelo)

    async def contar_por_produto_e_cor(self, produto_id: UUID, cor: str) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(ProdutoImagemModel)
            .where(ProdutoImagemModel.produto_id == produto_id, ProdutoImagemModel.cor == cor)
        )
        return int(total or 0)

    async def definir_principal(self, produto_id: UUID, imagem_id: UUID) -> ProdutoImagem | None:
        modelo = await self._session.get(ProdutoImagemModel, imagem_id)
        if modelo is None or modelo.produto_id != produto_id:
            return None
        # Dois UPDATEs sequenciais (desmarcar a antiga, depois marcar a
        # nova) em vez de um só, para nunca violar o índice único parcial
        # `uq_produto_imagem_principal_por_cor` mesmo dentro da mesma
        # transação — ver docs/data-model.md decisão #13.
        await self._session.execute(
            update(ProdutoImagemModel)
            .where(
                ProdutoImagemModel.produto_id == produto_id,
                ProdutoImagemModel.cor == modelo.cor,
                ProdutoImagemModel.principal.is_(True),
            )
            .values(principal=False)
        )
        modelo.principal = True
        await self._session.flush()
        return _imagem_para_entidade(modelo)

    async def atualizar_ordem(
        self, produto_id: UUID, imagem_id: UUID, *, ordem: int
    ) -> ProdutoImagem | None:
        modelo = await self._session.get(ProdutoImagemModel, imagem_id)
        if modelo is None or modelo.produto_id != produto_id:
            return None
        modelo.ordem = ordem
        await self._session.flush()
        return _imagem_para_entidade(modelo)

    async def remover(self, produto_id: UUID, imagem_id: UUID) -> ProdutoImagem | None:
        modelo = await self._session.get(ProdutoImagemModel, imagem_id)
        if modelo is None or modelo.produto_id != produto_id:
            return None
        entidade = _imagem_para_entidade(modelo)
        await self._session.delete(modelo)
        await self._session.flush()
        return entidade


class SqlAlchemyEstoqueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _query_base(self):
        return (
            select(
                EstoqueModel.variante_id,
                ProdutoVarianteModel.sku,
                ProdutoModel.nome.label("produto_nome"),
                EstoqueModel.quantidade,
                EstoqueModel.estoque_minimo,
            )
            .join(ProdutoVarianteModel, ProdutoVarianteModel.id == EstoqueModel.variante_id)
            .join(ProdutoModel, ProdutoModel.id == ProdutoVarianteModel.produto_id)
        )

    async def listar(
        self, *, page: int, per_page: int, sku: str | None
    ) -> tuple[list[Estoque], int]:
        offset, limit = offset_limit(page=page, per_page=per_page)
        query = self._query_base()
        if sku:
            query = query.where(ProdutoVarianteModel.sku.ilike(f"%{sku}%"))

        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        resultado = await self._session.execute(
            query.order_by(ProdutoVarianteModel.sku).offset(offset).limit(limit)
        )
        estoques = [_linha_para_estoque(linha) for linha in resultado.all()]
        return estoques, int(total or 0)

    async def listar_em_alerta(self) -> list[Estoque]:
        query = self._query_base().where(EstoqueModel.quantidade <= EstoqueModel.estoque_minimo)
        resultado = await self._session.execute(query.order_by(ProdutoVarianteModel.sku))
        return [_linha_para_estoque(linha) for linha in resultado.all()]

    async def buscar_por_variante(self, variante_id: UUID) -> Estoque | None:
        query = self._query_base().where(EstoqueModel.variante_id == variante_id)
        resultado = await self._session.execute(query)
        linha = resultado.first()
        return _linha_para_estoque(linha) if linha else None


class SqlAlchemyMovimentacaoRepository:
    """Implementação de `MovimentacaoRepository` — também atua como
    **EstoquePort** consumido pelo contexto de Vendas (ver domain/repositories.py).
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
    ) -> MovimentacaoEstoque:
        modelo = MovimentacaoEstoqueModel(
            id=uuid.uuid4(),
            variante_id=variante_id,
            tipo=tipo.value,
            quantidade=quantidade,
            motivo=motivo.value,
            pedido_id=pedido_id,
            fornecedor_id=fornecedor_id,
            usuario_id=usuario_id,
            criado_em=_now(),
        )
        self._session.add(modelo)
        try:
            # O INSERT dispara o trigger `trg_movimentacao_atualiza_estoque`
            # (AFTER INSERT), que aplica o delta em `estoque.quantidade` de
            # forma atômica e levanta SQLSTATE P0001 se o saldo for
            # insuficiente. A aplicação NUNCA faz UPDATE direto em `estoque`.
            await self._session.flush()
        except DBAPIError as exc:
            sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None)
            if sqlstate == _SQLSTATE_SALDO_INSUFICIENTE:
                detalhe = await self._montar_mensagem_saldo_insuficiente(
                    variante_id=variante_id, quantidade_solicitada=quantidade
                )
                raise SaldoDeEstoqueInsuficiente(detalhe) from exc
            if sqlstate == _SQLSTATE_DEADLOCK:
                # Rede de segurança — ver docs/data-model.md: mesmo ordenando
                # os itens por variante_id, um deadlock genuíno ainda pode
                # ocorrer em cenários adversos. A camada de aplicação (router
                # de Vendas) faz um retry único da transação inteira.
                await self._session.rollback()
                raise ConflitoTransacional(
                    "Conflito de concorrência detectado ao atualizar o estoque; tente novamente."
                ) from exc
            raise
        return _movimentacao_para_entidade(modelo, sku=None)

    async def _montar_mensagem_saldo_insuficiente(
        self, *, variante_id: UUID, quantidade_solicitada: int
    ) -> str:
        # A transação foi abortada pelo Postgres após o erro — é preciso um
        # rollback antes de qualquer nova query nesta sessão. Isso também
        # descarta quaisquer inserções anteriores desta mesma unit of work
        # (ex.: outros itens de um pedido multi-item), cumprindo o contrato
        # "nenhuma alteração parcial é persistida" (docs/openapi.yaml).
        await self._session.rollback()
        resultado = await self._session.execute(
            select(ProdutoVarianteModel.sku, EstoqueModel.quantidade)
            .join(EstoqueModel, EstoqueModel.variante_id == ProdutoVarianteModel.id)
            .where(ProdutoVarianteModel.id == variante_id)
        )
        linha = resultado.first()
        if linha is None:
            return (
                f"Variante {variante_id} possui saldo insuficiente para a "
                f"movimentação de {abs(quantidade_solicitada)} unidade(s)."
            )
        sku, saldo_atual = linha
        return (
            f"Variante {sku} possui {saldo_atual} unidade(s) em estoque, "
            f"foram solicitadas {abs(quantidade_solicitada)}."
        )

    async def listar(
        self,
        *,
        page: int,
        per_page: int,
        variante_id: UUID | None,
        tipo: TipoMovimentacao | None,
    ) -> tuple[list[MovimentacaoEstoque], int]:
        offset, limit = offset_limit(page=page, per_page=per_page)
        query = select(MovimentacaoEstoqueModel, ProdutoVarianteModel.sku).join(
            ProdutoVarianteModel, ProdutoVarianteModel.id == MovimentacaoEstoqueModel.variante_id
        )
        if variante_id is not None:
            query = query.where(MovimentacaoEstoqueModel.variante_id == variante_id)
        if tipo is not None:
            query = query.where(MovimentacaoEstoqueModel.tipo == tipo.value)

        total = await self._session.scalar(select(func.count()).select_from(query.subquery()))
        resultado = await self._session.execute(
            query.order_by(MovimentacaoEstoqueModel.criado_em.desc()).offset(offset).limit(limit)
        )
        movimentacoes = [
            _movimentacao_para_entidade(modelo, sku=sku) for modelo, sku in resultado.all()
        ]
        return movimentacoes, int(total or 0)


def _categoria_para_entidade(modelo: CategoriaModel) -> Categoria:
    return Categoria(id=modelo.id, nome=modelo.nome, slug=modelo.slug, ativo=modelo.ativo)


def _produto_para_entidade(modelo: ProdutoModel) -> Produto:
    return Produto(
        id=modelo.id,
        nome=modelo.nome,
        descricao=modelo.descricao,
        categoria_id=modelo.categoria_id,
        marca=modelo.marca,
        ativo=modelo.ativo,
        criado_em=modelo.criado_em,
    )


def _variante_para_entidade(modelo: ProdutoVarianteModel) -> ProdutoVariante:
    return ProdutoVariante(
        id=modelo.id,
        produto_id=modelo.produto_id,
        sku=modelo.sku,
        tamanho=modelo.tamanho,
        cor=modelo.cor,
        preco_venda=modelo.preco_venda,
        preco_custo=modelo.preco_custo,
        ativo=modelo.ativo,
    )


def _imagem_para_entidade(modelo: ProdutoImagemModel) -> ProdutoImagem:
    return ProdutoImagem(
        id=modelo.id,
        produto_id=modelo.produto_id,
        cor=modelo.cor,
        url=modelo.url,
        ordem=modelo.ordem,
        principal=modelo.principal,
        criado_em=modelo.criado_em,
    )


def _linha_para_estoque(linha) -> Estoque:
    return Estoque(
        variante_id=linha.variante_id,
        sku=linha.sku,
        produto_nome=linha.produto_nome,
        quantidade=linha.quantidade,
        estoque_minimo=linha.estoque_minimo,
    )


def _movimentacao_para_entidade(
    modelo: MovimentacaoEstoqueModel, *, sku: str | None
) -> MovimentacaoEstoque:
    return MovimentacaoEstoque(
        id=modelo.id,
        variante_id=modelo.variante_id,
        sku=sku or "",
        tipo=TipoMovimentacao(modelo.tipo),
        quantidade=modelo.quantidade,
        motivo=MotivoMovimentacao(modelo.motivo),
        pedido_id=modelo.pedido_id,
        fornecedor_id=modelo.fornecedor_id,
        usuario_id=modelo.usuario_id,
        criado_em=modelo.criado_em,
    )
