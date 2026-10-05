"""Controller público da vitrine online (prefixo `/loja`).

Único conjunto de rotas da API SEM autenticação JWT, além de `/health` e do
webhook de integração. Por isso:
  - só expõe leitura de catálogo ativo e o checkout (criação de pedido PENDENTE);
  - nunca confirma pagamento nem baixa estoque — isso exige a equipe, em
    `POST /pedidos/{id}/confirmar-pagamento` (contexto Vendas);
  - o nginx da vitrine só repassa `/api/loja/` (allow-list), ver
    apps/web/nginx.conf e docs/vitrine-online.md.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.vendas.application.use_cases.criar_pedido_vitrine import (
    CriarPedidoVitrineUseCase,
    ItemVitrineInput,
)
from amactive.contexts.vendas.infrastructure.persistence.gateways import (
    CatalogoEstoqueGateway,
    ClienteCadastrosGateway,
)
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
    SqlAlchemyReservaEstoqueRepository,
)
from amactive.contexts.vitrine.infrastructure.api.schemas import (
    CategoriaPublica,
    CategoriaRefPublica,
    CheckoutRequest,
    ImagemPublica,
    ItemPedidoPublico,
    OpcoesFiltroPublico,
    PedidoCheckoutPublico,
    ProdutoDetalhePublico,
    ProdutoListaPublica,
    ProdutoResumoPublico,
    VariantePublica,
)
from amactive.contexts.vitrine.infrastructure.persistence import consultas
from amactive.contexts.vitrine.infrastructure.persistence.consultas import (
    ProdutoVitrine,
)
from amactive.shared_kernel.database import get_db_session
from amactive.shared_kernel.exceptions import EntidadeNaoEncontrada, ErroDeValidacao
from amactive.shared_kernel.money import to_money_str
from amactive.shared_kernel.schemas import Pagination

router = APIRouter(prefix="/loja", tags=["Vitrine (público)"])


@router.get("/categorias", response_model=list[CategoriaPublica])
async def listar_categorias(
    session: AsyncSession = Depends(get_db_session),
) -> list[CategoriaPublica]:
    categorias = await consultas.listar_categorias(session)
    return [CategoriaPublica(id=c.id, nome=c.nome, slug=c.slug) for c in categorias]


@router.get("/filtros", response_model=OpcoesFiltroPublico)
async def listar_filtros(session: AsyncSession = Depends(get_db_session)) -> OpcoesFiltroPublico:
    opcoes = await consultas.listar_opcoes_filtro(session)
    return OpcoesFiltroPublico(cores=opcoes.cores, tamanhos=opcoes.tamanhos)


@router.get("/produtos", response_model=ProdutoListaPublica)
async def listar_produtos(
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=60),
    categoria_id: UUID | None = None,
    q: str | None = Query(default=None, max_length=100),
    cor: str | None = Query(default=None, max_length=50),
    tamanho: str | None = Query(default=None, max_length=10),
    preco_min: Decimal | None = Query(default=None, ge=0),
    preco_max: Decimal | None = Query(default=None, ge=0),
    ordem: Literal["nome", "preco_asc", "preco_desc", "desconto"] = "nome",
    session: AsyncSession = Depends(get_db_session),
) -> ProdutoListaPublica:
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise ErroDeValidacao("preco_min não pode ser maior que preco_max.")
    produtos, total = await consultas.listar_produtos(
        session,
        agora=datetime.now(UTC),
        page=page,
        per_page=per_page,
        categoria_id=categoria_id,
        busca=q,
        cor=cor,
        tamanho=tamanho,
        preco_min=preco_min,
        preco_max=preco_max,
        ordem=ordem,
    )
    return ProdutoListaPublica(
        data=[_resumo(p) for p in produtos],
        pagination=Pagination(total=total, page=page, per_page=per_page),
    )


@router.get("/produtos/{produto_id}", response_model=ProdutoDetalhePublico)
async def obter_produto(
    produto_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> ProdutoDetalhePublico:
    produto = await consultas.obter_produto(session, produto_id, agora=datetime.now(UTC))
    if produto is None:
        # Erro de domínio (RFC 7807), como no restante da API.
        raise EntidadeNaoEncontrada("Produto não encontrado.")
    resumo = _resumo(produto)
    return ProdutoDetalhePublico(
        **resumo.model_dump(),
        descricao=produto.descricao,
        variantes=[
            VariantePublica(
                id=v.id,
                sku=v.sku,
                tamanho=v.tamanho,
                cor=v.cor,
                preco_unitario=to_money_str(v.preco_unitario),
                preco_cheio=to_money_str(v.preco_cheio),
                disponivel=v.disponivel,
            )
            for v in produto.variantes
        ],
        imagens=[
            ImagemPublica(cor=i.cor, url=i.url, principal=i.principal) for i in produto.imagens
        ],
    )


@router.post(
    "/pedidos",
    response_model=PedidoCheckoutPublico,
    status_code=status.HTTP_201_CREATED,
    summary="Registra o pedido da vitrine e reserva o estoque (pagamento combinado via WhatsApp)",
)
async def criar_pedido_vitrine(
    payload: CheckoutRequest, session: AsyncSession = Depends(get_db_session)
) -> PedidoCheckoutPublico:
    gateway = CatalogoEstoqueGateway(session)
    use_case = CriarPedidoVitrineUseCase(
        SqlAlchemyPedidoRepository(session),
        gateway,
        gateway,
        ClienteCadastrosGateway(session),
        SqlAlchemyReservaEstoqueRepository(session),
    )
    pedido = await use_case.executar(
        cliente_nome=payload.cliente.nome,
        cliente_telefone=payload.cliente.telefone,
        observacao=payload.observacao,
        itens=[ItemVitrineInput(i.variante_id, i.quantidade) for i in payload.itens],
        agora=datetime.now(UTC),
    )
    await session.commit()

    descricoes = await consultas.descrever_variantes(
        session, [item.variante_id for item in pedido.itens]
    )
    assert pedido.reservado_ate is not None  # toda venda da vitrine nasce com reserva
    return PedidoCheckoutPublico(
        numero=pedido.numero,
        status=pedido.status.value,
        subtotal=to_money_str(pedido.subtotal),
        valor_total=to_money_str(pedido.valor_total),
        reservado_ate=pedido.reservado_ate,
        itens=[
            ItemPedidoPublico(
                sku=item.sku,
                descricao=descricoes.get(item.variante_id, item.sku),
                quantidade=item.quantidade,
                # subtotal = preço efetivo x quantidade (exato), então dividir
                # devolve o preço unitário promocional.
                preco_unitario=to_money_str(item.subtotal / item.quantidade),
                subtotal=to_money_str(item.subtotal),
            )
            for item in pedido.itens
        ],
    )


def _resumo(produto: ProdutoVitrine) -> ProdutoResumoPublico:
    principal = next((i for i in produto.imagens if i.principal), None)
    precos = [v.preco_unitario for v in produto.variantes]
    cores = sorted({v.cor for v in produto.variantes})
    return ProdutoResumoPublico(
        id=produto.id,
        nome=produto.nome,
        marca=produto.marca,
        categoria=(
            CategoriaRefPublica(id=produto.categoria_id, nome=produto.categoria_nome)
            if produto.categoria_id and produto.categoria_nome
            else None
        ),
        desconto_percentual=(
            to_money_str(produto.desconto_percentual)
            if produto.desconto_percentual is not None
            else None
        ),
        preco_a_partir_de=to_money_str(min(precos)),
        imagem_principal_url=principal.url if principal else None,
        cores=cores,
    )
