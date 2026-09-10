import { useQuery } from '@tanstack/react-query'
import { produtoService } from '../services/produto.service'

export function useProduto(id: string | undefined) {
  return useQuery({
    queryKey: ['produtos', 'detail', id],
    queryFn: () => produtoService.getById(id as string),
    enabled: Boolean(id),
    staleTime: 60_000,
  })
}
