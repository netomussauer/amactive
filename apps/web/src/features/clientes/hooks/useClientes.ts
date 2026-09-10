import { useQuery } from '@tanstack/react-query'
import { clienteService } from '../services/cliente.service'
import type { ClienteFilter } from '../types/cliente.types'

// staleTime 5min — clientes mudam pouco (docs/frontend-architecture.md §5.4).
export function useClientes(filter: ClienteFilter) {
  return useQuery({
    queryKey: ['clientes', 'list', filter],
    queryFn: () => clienteService.list(filter),
    staleTime: 5 * 60_000,
    placeholderData: (prev) => prev,
  })
}
