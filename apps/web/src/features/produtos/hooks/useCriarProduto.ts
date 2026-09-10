import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'
import type { CriarProdutoDTO } from '../types/produto.types'

export function useCriarProduto() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarProdutoDTO) => produtoService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos', 'list'] })
      toast.success('Produto cadastrado com sucesso!')
    },
  })
}
