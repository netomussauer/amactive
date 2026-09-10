import { useQuery } from '@tanstack/react-query'
import { estoqueService } from '../services/estoque.service'

export function useAlertasEstoque() {
  return useQuery({
    queryKey: ['estoque', 'alertas'],
    queryFn: () => estoqueService.listAlertas(),
    staleTime: 15_000,
  })
}
