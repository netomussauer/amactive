import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { pedidoService } from '../services/pedido.service'
import type { CriarPedidoDTO } from '../types/pedido.types'

// A venda altera dois agregados (pedido e estoque) — invalida ambos, além do
// resumo do dashboard. Ver docs/frontend-architecture.md §5.3.
export function useCriarPedido() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (dto: CriarPedidoDTO) => pedidoService.criar(dto),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pedidos'] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-resumo'] })
      toast.success('Venda confirmada com sucesso!')
    },
  })
}
