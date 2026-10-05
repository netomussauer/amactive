import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { pedidoService } from '../services/pedido.service'
import type { PagamentoRequest } from '../schemas/pedido.schema'

type Entrada = { id: string; pagamentos: PagamentoRequest[] }

export function useConfirmarPagamentoVitrine() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, pagamentos }: Entrada) => pedidoService.confirmarPagamentoVitrine(id, pagamentos),
    onSuccess: (_data, { id }) => {
      // Confirmar baixa estoque: invalida também a listagem de estoque.
      queryClient.invalidateQueries({ queryKey: ['pedidos'] })
      queryClient.invalidateQueries({ queryKey: ['pedidos', 'detail', id] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      toast.success('Pagamento confirmado. Estoque baixado.')
    },
  })
}
