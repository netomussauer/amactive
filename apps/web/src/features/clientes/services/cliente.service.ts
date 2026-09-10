import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import { ClienteListResponseSchema, ClienteResponseSchema, type CriarClienteDTO } from '../schemas/cliente.schema'
import type { ClienteFilter } from '../types/cliente.types'

export const clienteService = {
  async list(filter: ClienteFilter) {
    const raw = await apiClient<unknown>(`/clientes${buildQueryString(filter)}`)
    return ClienteListResponseSchema.parse(raw)
  },

  async getById(id: string) {
    const raw = await apiClient<unknown>(`/clientes/${id}`)
    return ClienteResponseSchema.parse(raw)
  },

  async create(payload: CriarClienteDTO) {
    const raw = await apiClient<unknown>('/clientes', { method: 'POST', body: JSON.stringify(payload) })
    return ClienteResponseSchema.parse(raw)
  },

  async update(id: string, payload: CriarClienteDTO) {
    const raw = await apiClient<unknown>(`/clientes/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
    return ClienteResponseSchema.parse(raw)
  },

  async inativar(id: string) {
    await apiClient<void>(`/clientes/${id}`, { method: 'DELETE' })
  },
}
