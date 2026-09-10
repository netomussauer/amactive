import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  EstoqueListResponseSchema,
  AlertaEstoqueListResponseSchema,
  MovimentacaoListResponseSchema,
  MovimentacaoResponseSchema,
  type CriarMovimentacaoDTO,
} from '../schemas/movimentacao.schema'
import type { EstoqueFilter, MovimentacaoFilter } from '../types/estoque.types'

export const estoqueService = {
  async list(filter: EstoqueFilter) {
    const raw = await apiClient<unknown>(`/estoque${buildQueryString(filter)}`)
    return EstoqueListResponseSchema.parse(raw)
  },

  async listAlertas() {
    const raw = await apiClient<unknown>('/estoque/alertas')
    return AlertaEstoqueListResponseSchema.parse(raw)
  },

  async listMovimentacoes(filter: MovimentacaoFilter) {
    const raw = await apiClient<unknown>(`/estoque/movimentacoes${buildQueryString(filter)}`)
    return MovimentacaoListResponseSchema.parse(raw)
  },

  async criarMovimentacao(payload: CriarMovimentacaoDTO) {
    const raw = await apiClient<unknown>('/estoque/movimentacoes', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    return MovimentacaoResponseSchema.parse(raw)
  },
}
