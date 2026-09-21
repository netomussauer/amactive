import { useQuery } from '@tanstack/react-query'
import { relatorioService } from '../services/relatorio.service'
import type { VendasPorPeriodoFilter } from '../types/relatorio.types'

export function useRelatorioVendas(filter: VendasPorPeriodoFilter) {
  return useQuery({
    queryKey: ['relatorios', 'vendas-por-periodo', filter],
    queryFn: () => relatorioService.vendasPorPeriodo(filter),
    staleTime: 60_000,
  })
}
