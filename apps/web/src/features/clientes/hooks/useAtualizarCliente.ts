import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { clienteService } from '../services/cliente.service'
import type { CriarClienteDTO } from '../types/cliente.types'

export function useAtualizarCliente(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarClienteDTO) => clienteService.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      toast.success('Cliente atualizado com sucesso!')
    },
  })
}
