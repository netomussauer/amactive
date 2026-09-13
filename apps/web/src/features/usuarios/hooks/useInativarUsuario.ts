import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { usuarioService } from '../services/usuario.service'

// Desativação (soft-delete, DELETE /usuarios/{id}). Salvaguarda do backend:
// não é possível desativar o único ADMIN ativo do sistema — 409 com
// `error.detail` explicativo, já exibido globalmente em toast por
// shared/lib/query-client.ts.
export function useInativarUsuario() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => usuarioService.inativar(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
      toast.success('Usuário desativado.')
    },
  })
}
