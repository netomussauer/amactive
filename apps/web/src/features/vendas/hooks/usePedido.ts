import { useQuery } from '@tanstack/react-query'
import { pedidoService } from '../services/pedido.service'

export function usePedido(id: string | undefined) {
  return useQuery({
    queryKey: ['pedidos', 'detail', id],
    queryFn: () => pedidoService.getById(id as string),
    enabled: Boolean(id),
    staleTime: 15_000,
  })
}
