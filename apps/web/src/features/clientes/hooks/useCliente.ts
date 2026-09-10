import { useQuery } from '@tanstack/react-query'
import { clienteService } from '../services/cliente.service'

export function useCliente(id: string | undefined) {
  return useQuery({
    queryKey: ['clientes', 'detail', id],
    queryFn: () => clienteService.getById(id as string),
    enabled: Boolean(id),
    staleTime: 5 * 60_000,
  })
}
