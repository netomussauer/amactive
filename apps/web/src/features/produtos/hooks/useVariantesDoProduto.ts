import { useQuery } from '@tanstack/react-query'
import { produtoService } from '../services/produto.service'

// Usado pelo PDV quando a busca é por nome do produto: depois de escolher o
// produto, lista as variantes (tamanho/cor/SKU/preço) para o operador escolher.
export function useVariantesDoProduto(produtoId: string | undefined) {
  return useQuery({
    queryKey: ['produtos', produtoId, 'variantes'],
    queryFn: () => produtoService.listVariantes(produtoId as string),
    enabled: Boolean(produtoId),
    staleTime: 60_000,
  })
}
