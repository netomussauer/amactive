import { useQuery } from '@tanstack/react-query'
import { usuarioService } from '../services/usuario.service'
import type { UsuarioFilter } from '../types/usuario.types'

// staleTime 60s — cadastro administrativo que muda pouco, mas mudanças de
// status/papel feitas por outro admin devem refletir rápido na lista.
export function useUsuarios(filter: UsuarioFilter) {
  return useQuery({
    queryKey: ['usuarios', 'list', filter],
    queryFn: () => usuarioService.list(filter),
    staleTime: 60_000,
    placeholderData: (prev) => prev,
  })
}
