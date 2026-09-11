import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { imagemService } from '../services/imagem.service'

export function useUploadImagem(produtoId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ cor, arquivo }: { cor: string; arquivo: File }) =>
      imagemService.upload(produtoId, cor, arquivo),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos', produtoId, 'imagens'] })
      toast.success('Imagem enviada com sucesso!')
    },
  })
}
