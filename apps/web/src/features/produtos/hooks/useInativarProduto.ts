import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'

export function useInativarProduto() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => produtoService.inativar(id),
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: ['produtos', 'list'] })
      queryClient.invalidateQueries({ queryKey: ['produtos', 'detail', id] })
      toast.success('Produto inativado.')
    },
  })
}
