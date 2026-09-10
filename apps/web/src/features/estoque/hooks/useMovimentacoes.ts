import { useQuery } from '@tanstack/react-query'
import { estoqueService } from '../services/estoque.service'
import type { MovimentacaoFilter } from '../types/estoque.types'

export function useMovimentacoes(filter: MovimentacaoFilter) {
  return useQuery({
    queryKey: ['estoque', 'movimentacoes', filter],
    queryFn: () => estoqueService.listMovimentacoes(filter),
    staleTime: 15_000,
    placeholderData: (prev) => prev,
  })
}
