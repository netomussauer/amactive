import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import { DashboardResumoResponseSchema } from '../schemas/dashboard.schema'
import type { DashboardFilter } from '../types/dashboard.types'

export const dashboardService = {
  async getResumo(filter: DashboardFilter) {
    const raw = await apiClient<unknown>(`/dashboard/resumo${buildQueryString(filter)}`)
    return DashboardResumoResponseSchema.parse(raw)
  },
}
