import { useQuery } from '@tanstack/react-query'
import { fornecedorService } from '../services/fornecedor.service'
import type { FornecedorFilter } from '../types/fornecedor.types'

export function useFornecedores(filter: FornecedorFilter) {
  return useQuery({
    queryKey: ['fornecedores', 'list', filter],
    queryFn: () => fornecedorService.list(filter),
    staleTime: 5 * 60_000,
    placeholderData: (prev) => prev,
  })
}
