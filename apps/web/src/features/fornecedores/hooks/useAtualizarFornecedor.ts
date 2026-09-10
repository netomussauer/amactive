import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { fornecedorService } from '../services/fornecedor.service'
import type { CriarFornecedorDTO } from '../types/fornecedor.types'

export function useAtualizarFornecedor(id: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarFornecedorDTO) => fornecedorService.update(id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fornecedores'] })
      toast.success('Fornecedor atualizado com sucesso!')
    },
  })
}
