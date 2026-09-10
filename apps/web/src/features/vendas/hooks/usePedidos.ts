import { useQuery } from '@tanstack/react-query'
import { pedidoService } from '../services/pedido.service'
import type { PedidoFilter } from '../types/pedido.types'

// staleTime 15s — lista de pedidos muda com frequência (docs/frontend-architecture.md §5.4).
export function usePedidos(filter: PedidoFilter) {
  return useQuery({
    queryKey: ['pedidos', 'list', filter],
    queryFn: () => pedidoService.list(filter),
    staleTime: 15_000,
    placeholderData: (prev) => prev,
  })
}
