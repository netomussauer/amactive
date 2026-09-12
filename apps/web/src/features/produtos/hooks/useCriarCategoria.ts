import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'
import type { CategoriaListResponse } from '../types/produto.types'
import type { CriarCategoriaDTO } from '../schemas/produto.schema'

// Criação rápida de categoria a partir do ProdutoForm (ver CriarCategoriaModal).
// Atualiza o cache de ['categorias'] otimisticamente (para a categoria nova
// aparecer no <select> assim que criada) e também invalida a query para
// buscar a lista definitiva (ordenação/slug vêm do backend).
export function useCriarCategoria() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: CriarCategoriaDTO) => produtoService.criarCategoria(payload),
    onSuccess: (categoria) => {
      queryClient.setQueryData<CategoriaListResponse>(['categorias'], (old) =>
        old ? { ...old, data: [...old.data, categoria] } : old,
      )
      queryClient.invalidateQueries({ queryKey: ['categorias'] })
      toast.success('Categoria criada com sucesso!')
    },
  })
}
