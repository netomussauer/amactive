import { useQuery } from '@tanstack/react-query'
import { usuarioService } from '../services/usuario.service'

export function useUsuario(id: string | undefined) {
  return useQuery({
    queryKey: ['usuarios', 'detail', id],
    queryFn: () => usuarioService.getById(id as string),
    enabled: Boolean(id),
    staleTime: 60_000,
  })
}
