import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'
import type { AtualizarProdutoDTO } from '../types/produto.types'

export function useAtualizarProduto(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: AtualizarProdutoDTO) => produtoService.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos', 'list'] })
      queryClient.invalidateQueries({ queryKey: ['produtos', 'detail', id] })
      toast.success('Produto atualizado com sucesso!')
    },
  })
}
