import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { imagemService } from '../services/imagem.service'

export function useRemoverImagem(produtoId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (imagemId: string) => imagemService.remover(produtoId, imagemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos', produtoId, 'imagens'] })
      toast.success('Imagem removida.')
    },
  })
}
