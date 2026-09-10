import { useQuery } from '@tanstack/react-query'
import { relatorioService } from '../services/relatorio.service'
import type { PeriodoFilter } from '../types/relatorio.types'

export function useRelatorioProdutos(filter: PeriodoFilter) {
  return useQuery({
    queryKey: ['relatorios', 'produtos-mais-vendidos', filter],
    queryFn: () => relatorioService.produtosMaisVendidos(filter),
    staleTime: 60_000,
  })
}
