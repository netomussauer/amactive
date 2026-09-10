import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  PedidoListResponseSchema,
  PedidoDetalheResponseSchema,
  CriarPedidoSchema,
  type CriarPedidoDTO,
} from '../schemas/pedido.schema'
import type { PedidoFilter } from '../types/pedido.types'

export const pedidoService = {
  async list(filter: PedidoFilter) {
    const raw = await apiClient<unknown>(`/pedidos${buildQueryString(filter)}`)
    return PedidoListResponseSchema.parse(raw)
  },

  async getById(id: string) {
    const raw = await apiClient<unknown>(`/pedidos/${id}`)
    return PedidoDetalheResponseSchema.parse(raw)
  },

  async criar(dto: CriarPedidoDTO) {
    const payload = CriarPedidoSchema.parse(dto)
    const raw = await apiClient<unknown>('/pedidos', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    return PedidoDetalheResponseSchema.parse(raw)
  },

  async cancelar(id: string) {
    const raw = await apiClient<unknown>(`/pedidos/${id}/cancelar`, { method: 'PATCH' })
    return PedidoDetalheResponseSchema.parse(raw)
  },
}
