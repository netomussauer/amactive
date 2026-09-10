import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { pedidoService } from '../services/pedido.service'

export function useCancelarPedido() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => pedidoService.cancelar(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] })
      queryClient.invalidateQueries({ queryKey: ['pedidos', 'detail', id] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      toast.success('Pedido cancelado.')
    },
  })
}
