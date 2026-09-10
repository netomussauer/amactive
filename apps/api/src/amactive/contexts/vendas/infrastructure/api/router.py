"""Controller (FastAPI APIRouter) do contexto Vendas."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.application.use_cases.cancelar_pedido import CancelarPedidoUseCase
from amactive.contexts.vendas.application.use_cases.consultar_pedidos import (
    ListarPedidosQuery,
    ObterPedidoQuery,
)
from amactive.contexts.vendas.application.use_cases.criar_pedido import CriarPedidoUseCase
from amactive.contexts.vendas.domain.entities import FormaPagamento, Pedido, StatusPedido
from amactive.contexts.vendas.infrastructure.api.schemas import (
    CriarPedidoRequest,
    ItemPedidoResponse,
    PagamentoResponse,
    PedidoDetalheResponse,
    PedidoListResponse,
    PedidoResponse,
)
from amactive.contexts.vendas.infrastructure.persistence.gateways import CatalogoEstoqueGateway
from amactive.contexts.vendas.infrastructure.persistence.repositories import (
    SqlAlchemyPedidoRepository,
)
from amactive.core.security import CurrentUser, get_current_user
from amactive.shared_kernel.database import get_db_session
from amactive.shared_kernel.exceptions import ConflitoTransacional
from amactive.shared_kernel.money import parse_money, to_money_str
from amactive.shared_kernel.schemas import Pagination

router = APIRouter(prefix="/pedidos", tags=["Pedidos"], dependencies=[Depends(get_current_user)])

_MAX_TENTATIVAS_DEADLOCK = 2


@router.get("", response_model=PedidoListResponse)
async def listar_pedidos(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_pedido: StatusPedido | None = Query(default=None, alias="status"),
    cliente_id: UUID | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> PedidoListResponse:
    pedidos, total = await ListarPedidosQuery(SqlAlchemyPedidoRepository(session)).executar(
        page=page,
        per_page=per_page,
        status=status_pedido,
        cliente_id=cliente_id,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    return PedidoListResponse(
        data=[_pedido_response(p) for p in pedidos],
        pagination=Pagination(total=total, page=page, per_page=per_page),
    )


@router.post("", response_model=PedidoDetalheResponse, status_code=status.HTTP_201_CREATED)
async def criar_pedido(
    payload: CriarPedidoRequest,
    session: AsyncSession = Depends(get_db_session),
    usuario: CurrentUser = Depends(get_current_user),
) -> PedidoDetalheResponse:
    itens = [
        ItemPedidoInput(
            variante_id=item.variante_id,
            quantidade=item.quantidade,
            desconto_item=parse_money(item.desconto_item),
        )
        for item in payload.itens
    ]
    pagamentos = [
        PagamentoInput(
            forma_pagamento=FormaPagamento(pagamento.forma_pagamento),
            valor=parse_money(pagamento.valor),
        )
        for pagamento in payload.pagamentos
    ]

    ultimo_erro: ConflitoTransacional | None = None
    pedido: Pedido | None = None
    for _tentativa in range(_MAX_TENTATIVAS_DEADLOCK):
        pedido_repo = SqlAlchemyPedidoRepository(session)
        gateway = CatalogoEstoqueGateway(session)
        use_case = CriarPedidoUseCase(pedido_repo, gateway, gateway)
        try:
            pedido = await use_case.executar(
                cliente_id=payload.cliente_id,
                desconto=parse_money(payload.desconto),
                observacao=payload.observacao,
                itens=itens,
                pagamentos=pagamentos,
                usuario_id=usuario.id,
            )
            ultimo_erro = None
            break
        except ConflitoTransacional as exc:
            ultimo_erro = exc
            continue

    if ultimo_erro is not None or pedido is None:
        raise ultimo_erro  # type: ignore[misc]

    await session.commit()
    return _pedido_detalhe_response(pedido)


@router.get("/{pedido_id}", response_model=PedidoDetalheResponse)
async def obter_pedido(
    pedido_id: UUID, session: AsyncSession = Depends(get_db_session)
) -> PedidoDetalheResponse:
    pedido = await ObterPedidoQuery(SqlAlchemyPedidoRepository(session)).executar(pedido_id)
    return _pedido_detalhe_response(pedido)


@router.patch("/{pedido_id}/cancelar", response_model=PedidoDetalheResponse)
async def cancelar_pedido(
    pedido_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    usuario: CurrentUser = Depends(get_current_user),
) -> PedidoDetalheResponse:
    pedido_repo = SqlAlchemyPedidoRepository(session)
    gateway = CatalogoEstoqueGateway(session)
    pedido = await CancelarPedidoUseCase(pedido_repo, gateway).executar(
        pedido_id, usuario_id=usuario.id
    )
    await session.commit()
    return _pedido_detalhe_response(pedido)


def _pedido_response(pedido: Pedido) -> PedidoResponse:
    return PedidoResponse(
        id=pedido.id,
        numero=pedido.numero,
        cliente_id=pedido.cliente_id,
        usuario_id=pedido.usuario_id,
        status=pedido.status.value,
        subtotal=to_money_str(pedido.subtotal),
        desconto=to_money_str(pedido.desconto),
        valor_total=to_money_str(pedido.valor_total),
        criado_em=pedido.criado_em,
        confirmado_em=pedido.confirmado_em,
    )


def _pedido_detalhe_response(pedido: Pedido) -> PedidoDetalheResponse:
    base = _pedido_response(pedido)
    return PedidoDetalheResponse(
        **base.model_dump(),
        itens=[
            ItemPedidoResponse(
                id=item.id,
                variante_id=item.variante_id,
                sku=item.sku,
                quantidade=item.quantidade,
                preco_unitario=to_money_str(item.preco_unitario),
                desconto_item=to_money_str(item.desconto_item),
                subtotal=to_money_str(item.subtotal),
            )
            for item in pedido.itens
        ],
        pagamentos=[
            PagamentoResponse(
                id=pagamento.id,
                forma_pagamento=pagamento.forma_pagamento.value,
                valor=to_money_str(pagamento.valor),
            )
            for pagamento in pedido.pagamentos
        ],
    )
