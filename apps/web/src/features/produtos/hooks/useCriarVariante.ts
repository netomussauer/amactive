import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'
import type { CriarVarianteDTO } from '../types/produto.types'

export function useCriarVariante(produtoId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarVarianteDTO) => produtoService.criarVariante(produtoId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos', 'detail', produtoId] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      toast.success('Variante (SKU) cadastrada com sucesso!')
    },
  })
}
