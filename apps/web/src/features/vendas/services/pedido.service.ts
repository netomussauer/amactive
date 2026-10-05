import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  PedidoListResponseSchema,
  PedidoDetalheResponseSchema,
  CriarPedidoSchema,
  type CriarPedidoDTO,
  type PagamentoRequest,
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

  // Pedido da vitrine: a equipe confirma o pagamento recebido pelo WhatsApp.
  // Só aqui o estoque é baixado (ver ConfirmarPagamentoVitrineUseCase no backend).
  async confirmarPagamentoVitrine(id: string, pagamentos: PagamentoRequest[]) {
    const raw = await apiClient<unknown>(`/pedidos/${id}/confirmar-pagamento`, {
      method: 'POST',
      body: JSON.stringify({ pagamentos }),
    })
    return PedidoDetalheResponseSchema.parse(raw)
  },
}
