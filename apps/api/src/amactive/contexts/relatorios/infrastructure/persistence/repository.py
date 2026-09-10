"""Repositório de leitura do contexto Relatórios & Dashboard.

`vw_vendas_por_periodo` já expõe a coluna `dia`, então o filtro de período é
um simples `WHERE dia BETWEEN` sobre a view. `vw_produtos_mais_vendidos` e
`vw_giro_estoque` (ver migrations/000001_initial_schema.up.sql) NÃO têm
dimensão de tempo — agregam o histórico inteiro — então, quando o caller
informa `data_inicio`/`data_fim`, este repositório usa uma query
parametrizada equivalente à lógica da view, mas filtrada por período, em vez
da view fixa. Sem filtro, o resultado é idêntico ao da view.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.relatorios.application.queries.dashboard_queries import (
    DashboardResumo,
    GiroEstoqueItem,
    ProdutoMaisVendido,
    VendaPorDia,
)


class RelatoriosRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def vendas_por_periodo(self, *, inicio: datetime, fim: datetime) -> list[VendaPorDia]:
        resultado = await self._session.execute(
            text(
                """
                SELECT dia::date AS dia, total_pedidos, COALESCE(faturamento, 0) AS faturamento
                FROM vw_vendas_por_periodo
                WHERE dia BETWEEN :inicio AND :fim
                ORDER BY dia
                """
            ),
            {"inicio": inicio, "fim": fim},
        )
        return [
            VendaPorDia(dia=row.dia, total_pedidos=row.total_pedidos, faturamento=row.faturamento)
            for row in resultado.all()
        ]

    async def produtos_mais_vendidos(
        self, *, inicio: datetime | None, fim: datetime | None, limite: int
    ) -> list[ProdutoMaisVendido]:
        condicoes = "p.status = 'CONFIRMADO'"
        parametros: dict[str, object] = {"limite": limite}
        if inicio is not None:
            condicoes += " AND p.confirmado_em >= :inicio"
            parametros["inicio"] = inicio
        if fim is not None:
            condicoes += " AND p.confirmado_em <= :fim"
            parametros["fim"] = fim

        resultado = await self._session.execute(
            text(
                f"""
                SELECT
                    ip.variante_id,
                    pv.sku,
                    pr.nome AS produto_nome,
                    SUM(ip.quantidade) AS quantidade_vendida,
                    SUM(ip.subtotal) AS faturamento
                FROM item_pedido ip
                JOIN pedido p ON p.id = ip.pedido_id
                JOIN produto_variante pv ON pv.id = ip.variante_id
                JOIN produto pr ON pr.id = pv.produto_id
                WHERE {condicoes}
                GROUP BY ip.variante_id, pv.sku, pr.nome
                ORDER BY quantidade_vendida DESC
                LIMIT :limite
                """
            ),
            parametros,
        )
        return [
            ProdutoMaisVendido(
                variante_id=row.variante_id,
                sku=row.sku,
                produto_nome=row.produto_nome,
                quantidade_vendida=row.quantidade_vendida,
                faturamento=row.faturamento,
            )
            for row in resultado.all()
        ]

    async def giro_estoque(
        self, *, inicio: datetime | None, fim: datetime | None
    ) -> list[GiroEstoqueItem]:
        condicoes = "me.tipo = 'SAIDA'"
        parametros: dict[str, object] = {}
        if inicio is not None:
            condicoes += " AND me.criado_em >= :inicio"
            parametros["inicio"] = inicio
        if fim is not None:
            condicoes += " AND me.criado_em <= :fim"
            parametros["fim"] = fim

        resultado = await self._session.execute(
            text(
                f"""
                SELECT
                    pv.id AS variante_id,
                    pv.sku,
                    COALESCE(SUM(CASE WHEN {condicoes} THEN me.quantidade ELSE 0 END), 0) AS total_saidas,
                    e.quantidade AS saldo_atual
                FROM produto_variante pv
                JOIN estoque e ON e.variante_id = pv.id
                LEFT JOIN movimentacao_estoque me ON me.variante_id = pv.id
                GROUP BY pv.id, pv.sku, e.quantidade
                ORDER BY total_saidas DESC
                """
            ),
            parametros,
        )
        return [
            GiroEstoqueItem(
                variante_id=row.variante_id,
                sku=row.sku,
                total_saidas=int(row.total_saidas),
                saldo_atual=row.saldo_atual,
            )
            for row in resultado.all()
        ]

    async def resumo_dashboard(
        self, *, inicio: datetime | None, fim: datetime | None
    ) -> DashboardResumo:
        condicoes = "status = 'CONFIRMADO'"
        parametros: dict[str, object] = {}
        if inicio is not None:
            condicoes += " AND confirmado_em >= :inicio"
            parametros["inicio"] = inicio
        if fim is not None:
            condicoes += " AND confirmado_em <= :fim"
            parametros["fim"] = fim

        resultado = await self._session.execute(
            text(
                f"""
                SELECT
                    COALESCE(SUM(valor_total), 0) AS faturamento,
                    COUNT(*) AS total_pedidos
                FROM pedido
                WHERE {condicoes}
                """
            ),
            parametros,
        )
        linha = resultado.one()
        faturamento: Decimal = linha.faturamento
        total_pedidos: int = linha.total_pedidos
        ticket_medio = (faturamento / total_pedidos) if total_pedidos > 0 else Decimal("0.00")

        alertas = await self._session.scalar(
            text("SELECT COUNT(*) FROM estoque WHERE quantidade <= estoque_minimo")
        )

        top_produtos = await self.produtos_mais_vendidos(inicio=inicio, fim=fim, limite=5)

        return DashboardResumo(
            faturamento_periodo=faturamento,
            total_pedidos_periodo=total_pedidos,
            ticket_medio=ticket_medio,
            variantes_em_alerta_estoque=int(alertas or 0),
            top_produtos=top_produtos,
        )
