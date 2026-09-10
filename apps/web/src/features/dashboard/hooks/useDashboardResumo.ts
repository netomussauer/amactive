import { useQuery } from '@tanstack/react-query'
import { dashboardService } from '../services/dashboard.service'
import type { DashboardFilter } from '../types/dashboard.types'

// staleTime 60s — indicadores agregados, não precisam de tempo real
// (docs/frontend-architecture.md §5.4).
export function useDashboardResumo(filter: DashboardFilter) {
  return useQuery({
    queryKey: ['dashboard-resumo', filter],
    queryFn: () => dashboardService.getResumo(filter),
    staleTime: 60_000,
  })
}
