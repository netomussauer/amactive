import { apiClient, apiUpload } from '@/shared/lib/api-client'
import { buildQueryString } from '@/shared/lib/build-query-string'
import {
  ImagemListResponseSchema,
  ImagemResponseSchema,
  type AtualizarOrdemImagemDTO,
} from '../schemas/imagem.schema'
import type { ImagemFilter } from '../types/imagem.types'

export const imagemService = {
  async list(produtoId: string, filter: ImagemFilter = {}) {
    const raw = await apiClient<unknown>(`/produtos/${produtoId}/imagens${buildQueryString(filter)}`)
    return ImagemListResponseSchema.parse(raw)
  },

  // multipart/form-data — cor precisa bater com uma cor de variante ativa do
  // produto (senão a API responde 422), arquivo até 5MB em jpeg/png/webp.
  async upload(produtoId: string, cor: string, arquivo: File) {
    const formData = new FormData()
    formData.append('cor', cor)
    formData.append('arquivo', arquivo)
    const raw = await apiUpload<unknown>(`/produtos/${produtoId}/imagens`, formData)
    return ImagemResponseSchema.parse(raw)
  },

  async definirPrincipal(produtoId: string, imagemId: string) {
    const raw = await apiClient<unknown>(`/produtos/${produtoId}/imagens/${imagemId}/principal`, {
      method: 'PATCH',
    })
    return ImagemResponseSchema.parse(raw)
  },

  async atualizarOrdem(produtoId: string, imagemId: string, payload: AtualizarOrdemImagemDTO) {
    const raw = await apiClient<unknown>(`/produtos/${produtoId}/imagens/${imagemId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
    return ImagemResponseSchema.parse(raw)
  },

  async remover(produtoId: string, imagemId: string) {
    await apiClient<void>(`/produtos/${produtoId}/imagens/${imagemId}`, { method: 'DELETE' })
  },
}
