import { z } from 'zod'
import { listResponseSchema } from '@/shared/types/common.types'

// Espelha components.schemas.ImagemResponse / ImagemListResponse /
// AtualizarOrdemImagemRequest do docs/openapi.yaml (tag "Imagens").
export const ImagemResponseSchema = z.object({
  id: z.string(),
  produto_id: z.string(),
  cor: z.string(),
  url: z.string(),
  ordem: z.number(),
  principal: z.boolean(),
  criado_em: z.string(),
})
export type Imagem = z.infer<typeof ImagemResponseSchema>

export const ImagemListResponseSchema = listResponseSchema(ImagemResponseSchema)
export type ImagemListResponse = z.infer<typeof ImagemListResponseSchema>

export const AtualizarOrdemImagemSchema = z.object({
  ordem: z.number().int().min(0),
})
export type AtualizarOrdemImagemDTO = z.infer<typeof AtualizarOrdemImagemSchema>
