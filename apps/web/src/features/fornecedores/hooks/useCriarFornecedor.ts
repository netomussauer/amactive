import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { fornecedorService } from '../services/fornecedor.service'
import type { CriarFornecedorDTO } from '../types/fornecedor.types'

export function useCriarFornecedor() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarFornecedorDTO) => fornecedorService.create(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] })
      toast.success('Fornecedor cadastrado com sucesso!')
    },
  })
}
