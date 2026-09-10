import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { estoqueService } from '../services/estoque.service'
import type { CriarMovimentacaoDTO } from '../types/estoque.types'

export function useCriarMovimentacao() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarMovimentacaoDTO) => estoqueService.criarMovimentacao(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['estoque'] })
      queryClient.invalidateQueries({ queryKey: ['produtos'] })
      toast.success('Movimentação registrada com sucesso!')
    },
  })
}
