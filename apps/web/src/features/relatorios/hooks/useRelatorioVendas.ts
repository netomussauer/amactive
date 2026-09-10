import { useQuery } from '@tanstack/react-query'
import { relatorioService } from '../services/relatorio.service'
import type { PeriodoFilter } from '../types/relatorio.types'

export function useRelatorioVendas(filter: Required<PeriodoFilter>) {
  return useQuery({
    queryKey: ['relatorios', 'vendas-por-periodo', filter],
    queryFn: () => relatorioService.vendasPorPeriodo(filter),
    staleTime: 60_000,
  })
}
