"""Controller (FastAPI APIRouter) do contexto Relatórios & Dashboard."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.relatorios.infrastructure.api.schemas import (
    DashboardResumoResponse,
    GiroEstoqueItemResponse,
    GiroEstoqueListResponse,
    ProdutoMaisVendidoListResponse,
    ProdutoMaisVendidoResponse,
    VendaPorDiaResponse,
    VendaPorPeriodoListResponse,
)
from amactive.contexts.relatorios.infrastructure.persistence.repository import (
    RelatoriosRepository,
)
from amactive.contexts.vendas.domain.entities import OrigemCanalPedido
from amactive.core.security import requer_papel
from amactive.shared_kernel.database import get_db_session
from amactive.shared_kernel.money import to_money_str

# Relatórios/Dashboard são restritos a ADMIN — ver matriz de permissões em
# docs/openapi.yaml.
router = APIRouter(dependencies=[Depends(requer_papel("ADMIN"))])


def _inicio_dia(d: date | None) -> datetime | None:
    return datetime.combine(d, time.min, tzinfo=UTC) if d else None


def _fim_dia(d: date | None) -> datetime | None:
    return datetime.combine(d, time.max, tzinfo=UTC) if d else None


@router.get("/dashboard/resumo", tags=["Relatorios"], response_model=DashboardResumoResponse)
async def obter_resumo_dashboard(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> DashboardResumoResponse:
    resumo = await RelatoriosRepository(session).resumo_dashboard(
        inicio=_inicio_dia(data_inicio), fim=_fim_dia(data_fim)
    )
    return DashboardResumoResponse(
        faturamento_periodo=to_money_str(resumo.faturamento_periodo),
        total_pedidos_periodo=resumo.total_pedidos_periodo,
        ticket_medio=to_money_str(resumo.ticket_medio),
        variantes_em_alerta_estoque=resumo.variantes_em_alerta_estoque,
        top_produtos=[
            ProdutoMaisVendidoResponse(
                variante_id=p.variante_id,
                sku=p.sku,
                produto_nome=p.produto_nome,
                quantidade_vendida=p.quantidade_vendida,
                faturamento=to_money_str(p.faturamento),
            )
            for p in resumo.top_produtos
        ],
    )


@router.get(
    "/relatorios/vendas-por-periodo",
    tags=["Relatorios"],
    response_model=VendaPorPeriodoListResponse,
)
async def relatorio_vendas_por_periodo(
    data_inicio: date,
    data_fim: date,
    origem_canal: OrigemCanalPedido | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> VendaPorPeriodoListResponse:
    vendas = await RelatoriosRepository(session).vendas_por_periodo(
        inicio=datetime.combine(data_inicio, time.min, tzinfo=UTC),
        fim=datetime.combine(data_fim, time.max, tzinfo=UTC),
        origem_canal=origem_canal.value if origem_canal is not None else None,
    )
    return VendaPorPeriodoListResponse(
        data=[
            VendaPorDiaResponse(
                dia=v.dia, total_pedidos=v.total_pedidos, faturamento=to_money_str(v.faturamento)
            )
            for v in vendas
        ]
    )


@router.get(
    "/relatorios/produtos-mais-vendidos",
    tags=["Relatorios"],
    response_model=ProdutoMaisVendidoListResponse,
)
async def relatorio_produtos_mais_vendidos(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    per_page: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> ProdutoMaisVendidoListResponse:
    produtos = await RelatoriosRepository(session).produtos_mais_vendidos(
        inicio=_inicio_dia(data_inicio), fim=_fim_dia(data_fim), limite=per_page
    )
    return ProdutoMaisVendidoListResponse(
        data=[
            ProdutoMaisVendidoResponse(
                variante_id=p.variante_id,
                sku=p.sku,
                produto_nome=p.produto_nome,
                quantidade_vendida=p.quantidade_vendida,
                faturamento=to_money_str(p.faturamento),
            )
            for p in produtos
        ]
    )


@router.get("/relatorios/giro-estoque", tags=["Relatorios"], response_model=GiroEstoqueListResponse)
async def relatorio_giro_estoque(
    data_inicio: date | None = None,
    data_fim: date | None = None,
    session: AsyncSession = Depends(get_db_session),
) -> GiroEstoqueListResponse:
    itens = await RelatoriosRepository(session).giro_estoque(
        inicio=_inicio_dia(data_inicio), fim=_fim_dia(data_fim)
    )
    return GiroEstoqueListResponse(
        data=[
            GiroEstoqueItemResponse(
                variante_id=i.variante_id,
                sku=i.sku,
                total_saidas=i.total_saidas,
                saldo_atual=i.saldo_atual,
            )
            for i in itens
        ]
    )
