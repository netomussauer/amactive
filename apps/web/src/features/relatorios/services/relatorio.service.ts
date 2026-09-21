import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  VendasPorPeriodoResponseSchema,
  ProdutosMaisVendidosResponseSchema,
  GiroEstoqueResponseSchema,
} from '../schemas/relatorio.schema'
import type { PeriodoFilter, VendasPorPeriodoFilter } from '../types/relatorio.types'

export const relatorioService = {
  async vendasPorPeriodo(filter: VendasPorPeriodoFilter) {
    const raw = await apiClient<unknown>(`/relatorios/vendas-por-periodo${buildQueryString(filter)}`)
    return VendasPorPeriodoResponseSchema.parse(raw)
  },

  async produtosMaisVendidos(filter: PeriodoFilter) {
    const raw = await apiClient<unknown>(`/relatorios/produtos-mais-vendidos${buildQueryString(filter)}`)
    return ProdutosMaisVendidosResponseSchema.parse(raw)
  },

  async giroEstoque(filter: PeriodoFilter) {
    const raw = await apiClient<unknown>(`/relatorios/giro-estoque${buildQueryString(filter)}`)
    return GiroEstoqueResponseSchema.parse(raw)
  },
}
