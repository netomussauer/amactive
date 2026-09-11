import { useQuery } from '@tanstack/react-query'
import { imagemService } from '../services/imagem.service'
import type { ImagemFilter } from '../types/imagem.types'

// Galeria de imagens do produto (opcionalmente filtrada por cor). Imagens
// mudam pouco — staleTime mais longo, igual a clientes/fornecedores.
export function useImagensDoProduto(produtoId: string | undefined, filter: ImagemFilter = {}) {
  return useQuery({
    queryKey: ['produtos', produtoId, 'imagens', filter.cor ?? null],
    queryFn: () => imagemService.list(produtoId as string, filter),
    enabled: Boolean(produtoId),
    staleTime: 60_000,
  })
}
