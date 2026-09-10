import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'
import type { AtualizarVarianteDTO } from '../types/produto.types'

export function useAtualizarVariante(produtoId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ varianteId, payload }: { varianteId: string; payload: AtualizarVarianteDTO }) =>
      produtoService.atualizarVariante(varianteId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos', 'detail', produtoId] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      toast.success('Variante atualizada com sucesso!')
    },
  })
}
