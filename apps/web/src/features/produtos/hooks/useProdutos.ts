import { useQuery } from '@tanstack/react-query'
import { produtoService } from '../services/produto.service'
import type { ProdutoFilter } from '../types/produto.types'

// staleTime 60s — lista de produtos/variantes muda pouco durante o expediente
// (docs/frontend-architecture.md §5.4).
export function useProdutos(filter: ProdutoFilter) {
  return useQuery({
    queryKey: ['produtos', 'list', filter],
    queryFn: () => produtoService.list(filter),
    staleTime: 60_000,
    placeholderData: (prev) => prev,
  })
}
