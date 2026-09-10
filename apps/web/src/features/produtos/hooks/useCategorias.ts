import { useQuery } from '@tanstack/react-query'
import { produtoService } from '../services/produto.service'

// staleTime longo — categorias mudam raramente, mesma lógica de clientes/fornecedores.
export function useCategorias() {
  return useQuery({
    queryKey: ['categorias'],
    queryFn: () => produtoService.listCategorias(),
    staleTime: 5 * 60_000,
  })
}
