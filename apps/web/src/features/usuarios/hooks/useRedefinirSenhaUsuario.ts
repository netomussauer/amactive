import { useMutation } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { usuarioService } from '../services/usuario.service'
import type { RedefinirSenhaDTO } from '../types/usuario.types'

// Reset administrativo de senha (PATCH /usuarios/{id}/senha) — o ADMIN
// define a senha nova diretamente, sem enviar e-mail nem exigir a senha
// atual. Não invalida nenhuma query: senha nunca aparece em resposta
// alguma da API.
export function useRedefinirSenhaUsuario(id: string) {
  return useMutation({
    mutationFn: (payload: RedefinirSenhaDTO) => usuarioService.redefinirSenha(id, payload),
    onSuccess: () => {
      toast.success('Senha redefinida com sucesso.')
    },
  })
}
