import { useMutation, useQueryClient } from '@tanstack/react-query'
import { imagemService } from '../services/imagem.service'
import type { AtualizarOrdemImagemDTO } from '../types/imagem.types'

// Sem toast de sucesso — é usado em sequência (setas de reordenar), um toast
// por clique seria ruído. Erros continuam caindo no toast global (query-client.ts).
export function useAtualizarOrdemImagem(produtoId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ imagemId, payload }: { imagemId: string; payload: AtualizarOrdemImagemDTO }) =>
      imagemService.atualizarOrdem(produtoId, imagemId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['produtos', produtoId, 'imagens'] })
    },
  })
}
