"""Queries de leitura (CQRS-lite — ver docs/SDD.md §1.5) para o contexto
Relatórios & Dashboard. Sem tabelas de escrita próprias: lê de views SQL
(`vw_*`, ver migrations/000001_initial_schema.up.sql) ou de queries de
agregação parametrizadas quando a view não suporta filtro de período.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class VendaPorDia:
    dia: date
    total_pedidos: int
    faturamento: Decimal


@dataclass(frozen=True)
class ProdutoMaisVendido:
    variante_id: UUID
    sku: str
    produto_nome: str
    quantidade_vendida: int
    faturamento: Decimal


@dataclass(frozen=True)
class GiroEstoqueItem:
    variante_id: UUID
    sku: str
    total_saidas: int
    saldo_atual: int


@dataclass(frozen=True)
class DashboardResumo:
    faturamento_periodo: Decimal
    total_pedidos_periodo: int
    ticket_medio: Decimal
    variantes_em_alerta_estoque: int
    top_produtos: list[ProdutoMaisVendido]


def periodo_para_datetimes(
    data_inicio: date | None, data_fim: date | None
) -> tuple[datetime | None, datetime | None]:
    inicio = datetime.combine(data_inicio, time.min, tzinfo=UTC) if data_inicio else None
    fim = datetime.combine(data_fim, time.max, tzinfo=UTC) if data_fim else None
    return inicio, fim
