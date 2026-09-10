import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { clienteService } from '../services/cliente.service'
import type { CriarClienteDTO } from '../types/cliente.types'

export function useCriarCliente() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarClienteDTO) => clienteService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      toast.success('Cliente cadastrado com sucesso!')
    },
  })
}
