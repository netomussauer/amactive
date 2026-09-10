import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { fornecedorService } from '../services/fornecedor.service'

export function useInativarFornecedor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: string) => fornecedorService.inativar(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] })
      toast.success('Fornecedor inativado.')
    },
  })
}
