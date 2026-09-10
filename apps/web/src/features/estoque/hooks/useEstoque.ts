import { useQuery } from '@tanstack/react-query'
import { estoqueService } from '../services/estoque.service'
import type { EstoqueFilter } from '../types/estoque.types'

// staleTime 15s — saldo muda com frequência durante o expediente
// (docs/frontend-architecture.md §5.4).
export function useEstoque(filter: EstoqueFilter) {
  return useQuery({
    queryKey: ['estoque', 'list', filter],
    queryFn: () => estoqueService.list(filter),
    staleTime: 15_000,
    placeholderData: (prev) => prev,
  })
}
