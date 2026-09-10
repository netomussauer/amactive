"""Schemas HTTP (Pydantic) — espelham docs/openapi.yaml (Relatórios & Dashboard)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class VendaPorDiaResponse(BaseModel):
    dia: date
    total_pedidos: int
    faturamento: str


class VendaPorPeriodoListResponse(BaseModel):
    data: list[VendaPorDiaResponse]


class ProdutoMaisVendidoResponse(BaseModel):
    variante_id: UUID
    sku: str
    produto_nome: str
    quantidade_vendida: int
    faturamento: str


class ProdutoMaisVendidoListResponse(BaseModel):
    data: list[ProdutoMaisVendidoResponse]


class GiroEstoqueItemResponse(BaseModel):
    variante_id: UUID
    sku: str
    total_saidas: int
    saldo_atual: int


class GiroEstoqueListResponse(BaseModel):
    data: list[GiroEstoqueItemResponse]


class DashboardResumoResponse(BaseModel):
    faturamento_periodo: str
    total_pedidos_periodo: int
    ticket_medio: str
    variantes_em_alerta_estoque: int
    top_produtos: list[ProdutoMaisVendidoResponse]
