import { apiClient } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  ProdutoListResponseSchema,
  ProdutoResponseSchema,
  ProdutoDetalheResponseSchema,
  VarianteListResponseSchema,
  VarianteResponseSchema,
  CategoriaListResponseSchema,
  type CriarProdutoDTO,
  type AtualizarProdutoDTO,
  type CriarVarianteDTO,
  type AtualizarVarianteDTO,
} from '../schemas/produto.schema'
import type { ProdutoFilter } from '../types/produto.types'

export const produtoService = {
  async list(filter: ProdutoFilter) {
    const raw = await apiClient<unknown>(`/produtos${buildQueryString(filter)}`)
    return ProdutoListResponseSchema.parse(raw)
  },

  async getById(id: string) {
    const raw = await apiClient<unknown>(`/produtos/${id}`)
    return ProdutoDetalheResponseSchema.parse(raw)
  },

  async create(payload: CriarProdutoDTO) {
    const raw = await apiClient<unknown>('/produtos', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    return ProdutoResponseSchema.parse(raw)
  },

  async update(id: string, payload: AtualizarProdutoDTO) {
    const raw = await apiClient<unknown>(`/produtos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
    return ProdutoResponseSchema.parse(raw)
  },

  async inativar(id: string) {
    await apiClient<void>(`/produtos/${id}`, { method: 'DELETE' })
  },

  async listVariantes(produtoId: string) {
    const raw = await apiClient<unknown>(`/produtos/${produtoId}/variantes`)
    return VarianteListResponseSchema.parse(raw)
  },

  async criarVariante(produtoId: string, payload: CriarVarianteDTO) {
    const raw = await apiClient<unknown>(`/produtos/${produtoId}/variantes`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    return VarianteResponseSchema.parse(raw)
  },

  async getVariante(varianteId: string) {
    const raw = await apiClient<unknown>(`/variantes/${varianteId}`)
    return VarianteResponseSchema.parse(raw)
  },

  async atualizarVariante(varianteId: string, payload: AtualizarVarianteDTO) {
    const raw = await apiClient<unknown>(`/variantes/${varianteId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
    return VarianteResponseSchema.parse(raw)
  },

  async inativarVariante(varianteId: string) {
    await apiClient<void>(`/variantes/${varianteId}`, { method: 'DELETE' })
  },

  async listCategorias() {
    const raw = await apiClient<unknown>('/categorias')
    return CategoriaListResponseSchema.parse(raw)
  },

  // Busca composta usada pelo PDV: /estoque?sku= resolve o variante_id pelo
  // SKU exato, depois /variantes/{id} traz preço/tamanho/cor completos — o
  // contrato de API (docs/openapi.yaml) não expõe um único endpoint de busca
  // de variante por SKU, então combinamos os dois aqui.
  async buscarVariantePorSku(sku: string) {
    const estoqueRaw = await apiClient<{
      data: Array<{ variante_id: string; sku: string; produto_nome: string }>
    }>(`/estoque${buildQueryString({ sku, per_page: 5 })}`)

    const match = estoqueRaw.data.find((item) => item.sku.toLowerCase() === sku.toLowerCase())
    if (!match) return null

    const variante = await this.getVariante(match.variante_id)
    return { variante, produtoNome: match.produto_nome }
  },
}
