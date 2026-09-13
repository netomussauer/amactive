import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { usuarioService } from '../services/usuario.service'
import type { AtualizarUsuarioDTO } from '../types/usuario.types'

// Usado pelo formulário de edição (UsuarioEditForm, nome+papel) — o
// chamador é responsável por reenviar o `ativo` atual junto com o payload,
// já que a API exige os três campos em PUT /usuarios/{id} (ver
// docs/openapi.yaml AtualizarUsuarioRequest). Para o toggle
// desativar/reativar, ver useInativarUsuario/useReativarUsuario.
//
// Salvaguarda do backend: um usuário não pode rebaixar o próprio papel de
// ADMIN sendo o único ADMIN ativo do sistema — 409 com `error.detail`
// explicativo, já exibido globalmente em toast por
// shared/lib/query-client.ts.
export function useAtualizarUsuario(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: AtualizarUsuarioDTO) => usuarioService.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
      toast.success('Usuário atualizado com sucesso!')
    },
  })
}
