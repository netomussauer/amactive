import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { usuarioService } from '../services/usuario.service'
import type { CriarUsuarioDTO } from '../types/usuario.types'

export function useCriarUsuario() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarUsuarioDTO) => usuarioService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
      toast.success('Usuário cadastrado com sucesso!')
    },
  })
}
