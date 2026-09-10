import { z } from 'zod'
import { paginatedResponseSchema, listResponseSchema } from '@/shared/types/common.types'

// Espelha docs/openapi.yaml components.schemas.TipoMovimentacao
export const TipoMovimentacao = {
  ENTRADA: 'ENTRADA',
  SAIDA: 'SAIDA',
  AJUSTE: 'AJUSTE',
} as const
export const TipoMovimentacaoSchema = z.enum(['ENTRADA', 'SAIDA', 'AJUSTE'])
export type TipoMovimentacao = z.infer<typeof TipoMovimentacaoSchema>

export const MotivoMovimentacao = {
  COMPRA: 'COMPRA',
  AJUSTE_INVENTARIO: 'AJUSTE_INVENTARIO',
  DEVOLUCAO: 'DEVOLUCAO',
  PERDA: 'PERDA',
} as const
export const MotivoMovimentacaoSchema = z.enum(['COMPRA', 'AJUSTE_INVENTARIO', 'DEVOLUCAO', 'PERDA'])
export type MotivoMovimentacao = z.infer<typeof MotivoMovimentacaoSchema>

export const EstoqueResponseSchema = z.object({
  variante_id: z.string(),
  sku: z.string(),
  produto_nome: z.string(),
  quantidade: z.number(),
  estoque_minimo: z.number(),
  em_alerta: z.boolean(),
})
export type EstoqueItem = z.infer<typeof EstoqueResponseSchema>

export const EstoqueListResponseSchema = paginatedResponseSchema(EstoqueResponseSchema)
export type EstoqueListResponse = z.infer<typeof EstoqueListResponseSchema>

export const AlertaEstoqueListResponseSchema = listResponseSchema(EstoqueResponseSchema)

export const CriarMovimentacaoSchema = z.object({
  variante_id: z.string().uuid({ message: 'Selecione uma variante' }),
  tipo: TipoMovimentacaoSchema,
  quantidade: z.number().int().min(1, 'Quantidade mínima é 1'),
  motivo: MotivoMovimentacaoSchema,
  fornecedor_id: z.string().uuid().nullable().optional(),
})
export type CriarMovimentacaoDTO = z.infer<typeof CriarMovimentacaoSchema>

export const MovimentacaoResponseSchema = z.object({
  id: z.string(),
  variante_id: z.string(),
  sku: z.string(),
  tipo: TipoMovimentacaoSchema,
  quantidade: z.number(),
  motivo: z.string(),
  pedido_id: z.string().nullable().optional(),
  fornecedor_id: z.string().nullable().optional(),
  usuario_id: z.string(),
  criado_em: z.string(),
})
export type Movimentacao = z.infer<typeof MovimentacaoResponseSchema>

export const MovimentacaoListResponseSchema = paginatedResponseSchema(MovimentacaoResponseSchema)
export type MovimentacaoListResponse = z.infer<typeof MovimentacaoListResponseSchema>
