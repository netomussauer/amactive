import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  FornecedorListResponseSchema,
  FornecedorResponseSchema,
  type CriarFornecedorDTO,
} from '../schemas/fornecedor.schema'
import type { FornecedorFilter } from '../types/fornecedor.types'

export const fornecedorService = {
  async list(filter: FornecedorFilter) {
    const raw = await apiClient<unknown>(`/fornecedores${buildQueryString(filter)}`)
    return FornecedorListResponseSchema.parse(raw)
  },

  async getById(id: string) {
    const raw = await apiClient<unknown>(`/fornecedores/${id}`)
    return FornecedorResponseSchema.parse(raw)
  },

  async create(payload: CriarFornecedorDTO) {
    const raw = await apiClient<unknown>('/fornecedores', { method: 'POST', body: JSON.stringify(payload) })
    return FornecedorResponseSchema.parse(raw)
  },

  async update(id: string, payload: CriarFornecedorDTO) {
    const raw = await apiClient<unknown>(`/fornecedores/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
    return FornecedorResponseSchema.parse(raw)
  },

  async inativar(id: string) {
    await apiClient<void>(`/fornecedores/${id}`, { method: 'DELETE' })
  },
}
