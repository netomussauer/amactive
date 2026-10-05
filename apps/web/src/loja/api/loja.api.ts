// Acesso à API pública da vitrine. Usa o mesmo apiClient do sistema (erros em
// RFC 7807, toast global), mas sem token: as rotas /loja não exigem login.

import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  CategoriasLojaSchema,
  PedidoCheckoutLojaSchema,
  ProdutoDetalheLojaSchema,
  ProdutoListaLojaSchema,
  type CheckoutLojaRequest,
} from '../schemas/loja.schema'

export type FiltrosProdutosLoja = {
  page: number
  per_page: number
  categoria_id?: string
  q?: string
}

export async function listarCategoriasLoja() {
  return CategoriasLojaSchema.parse(await apiClient<unknown>('/loja/categorias'))
}

export async function listarProdutosLoja(filtros: FiltrosProdutosLoja) {
  const qs = buildQueryString(filtros)
  return ProdutoListaLojaSchema.parse(await apiClient<unknown>(`/loja/produtos${qs}`))
}

export async function obterProdutoLoja(produtoId: string) {
  return ProdutoDetalheLojaSchema.parse(
    await apiClient<unknown>(`/loja/produtos/${encodeURIComponent(produtoId)}`),
  )
}

export async function criarPedidoLoja(payload: CheckoutLojaRequest) {
  return PedidoCheckoutLojaSchema.parse(
    await apiClient<unknown>('/loja/pedidos', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  )
}
