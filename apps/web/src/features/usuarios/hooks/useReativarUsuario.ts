import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { usuarioService } from '../services/usuario.service'
import type { PapelUsuario } from '@/shared/types/api.types'

type ReativarUsuarioInput = { id: string; nome: string; papel: PapelUsuario }

// Não existe endpoint dedicado de reativação — a API exige nome/papel
// completos em PUT /usuarios/{id} (ver docs/openapi.yaml
// AtualizarUsuarioRequest), então reenviamos os valores atuais do usuário
// junto com ativo: true. Usado tanto pela tabela (UsuarioTable) quanto pelo
// detalhe (UsuarioDetalhePage) para manter a mesma ação em um só lugar.
export function useReativarUsuario() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, nome, papel }: ReativarUsuarioInput) =>
      usuarioService.update(id, { nome, papel, ativo: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['usuarios'] })
      toast.success('Usuário reativado.')
    },
  })
}
