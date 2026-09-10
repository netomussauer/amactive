import { useQuery } from '@tanstack/react-query'
import { relatorioService } from '../services/relatorio.service'
import type { PeriodoFilter } from '../types/relatorio.types'

export function useRelatorioGiroEstoque(filter: PeriodoFilter) {
  return useQuery({
    queryKey: ['relatorios', 'giro-estoque', filter],
    queryFn: () => relatorioService.giroEstoque(filter),
    staleTime: 60_000,
  })
}
