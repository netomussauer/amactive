import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { clienteService } from '../services/cliente.service'

export function useInativarCliente() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => clienteService.inativar(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clientes'] })
      toast.success('Cliente inativado.')
    },
  })
}
