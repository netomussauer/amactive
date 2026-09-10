import { useQuery } from '@tanstack/react-query'
import { fornecedorService } from '../services/fornecedor.service'

export function useFornecedor(id: string | undefined) {
  return useQuery({
    queryKey: ['fornecedores', 'detail', id],
    queryFn: () => fornecedorService.getById(id as string),
    enabled: Boolean(id),
    staleTime: 5 * 60_000,
  })
}
