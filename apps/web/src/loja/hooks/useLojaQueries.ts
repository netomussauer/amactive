import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import {
  criarPedidoLoja,
  listarCategoriasLoja,
  listarProdutosLoja,
  obterProdutoLoja,
  type FiltrosProdutosLoja,
} from '../api/loja.api'
import type { CheckoutLojaRequest } from '../schemas/loja.schema'

const CHAVE = ['loja'] as const

export function useCategoriasLoja() {
  return useQuery({
    queryKey: [...CHAVE, 'categorias'],
    queryFn: listarCategoriasLoja,
    staleTime: 5 * 60_000,
  })
}

export function useProdutosLoja(filtros: FiltrosProdutosLoja) {
  return useQuery({
    queryKey: [...CHAVE, 'produtos', filtros],
    queryFn: () => listarProdutosLoja(filtros),
    // Troca de página/filtro mantém a grade anterior até chegar a nova — sem piscar.
    placeholderData: keepPreviousData,
  })
}

export function useProdutoLoja(produtoId: string) {
  return useQuery({
    queryKey: [...CHAVE, 'produto', produtoId],
    queryFn: () => obterProdutoLoja(produtoId),
    enabled: produtoId.length > 0,
  })
}

export function useCriarPedidoLoja() {
  return useMutation({
    mutationFn: (payload: CheckoutLojaRequest) => criarPedidoLoja(payload),
    // Sem retry: o checkout cria um pedido — repetir pode duplicar a reserva.
    retry: false,
  })
}
