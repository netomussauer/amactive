import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'

export function useInativarVariante(produtoId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (varianteId: string) => produtoService.inativarVariante(varianteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos', 'detail', produtoId] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      toast.success('Variante inativada.')
    },
  })
}
