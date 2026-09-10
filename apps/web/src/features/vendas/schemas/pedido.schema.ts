import { z } from 'zod'
import { paginatedResponseSchema } from '@/shared/types/common.types'

// Espelha docs/openapi.yaml components.schemas.StatusPedido / FormaPagamento
export const StatusPedido = {
  PENDENTE: 'PENDENTE',
  CONFIRMADO: 'CONFIRMADO',
  CANCELADO: 'CANCELADO',
} as const
export const StatusPedidoSchema = z.enum(['PENDENTE', 'CONFIRMADO', 'CANCELADO'])
export type StatusPedido = z.infer<typeof StatusPedidoSchema>

export const FormaPagamento = {
  DINHEIRO: 'DINHEIRO',
  PIX: 'PIX',
  CARTAO_DEBITO: 'CARTAO_DEBITO',
  CARTAO_CREDITO: 'CARTAO_CREDITO',
} as const
export const FormaPagamentoSchema = z.enum(['DINHEIRO', 'PIX', 'CARTAO_DEBITO', 'CARTAO_CREDITO'])
export type FormaPagamento = z.infer<typeof FormaPagamentoSchema>

const decimalString = z.string().regex(/^\d+\.\d{2}$/, 'Formato inválido: use 129.90')

// ── Requests ──
export const ItemPedidoRequestSchema = z.object({
  variante_id: z.string().uuid(),
  quantidade: z.number().int().min(1, 'Quantidade mínima é 1'),
  desconto_item: decimalString.default('0.00'),
})
export type ItemPedidoRequest = z.infer<typeof ItemPedidoRequestSchema>

export const PagamentoRequestSchema = z.object({
  forma_pagamento: FormaPagamentoSchema,
  valor: decimalString,
})
export type PagamentoRequest = z.infer<typeof PagamentoRequestSchema>

export const CriarPedidoSchema = z.object({
  cliente_id: z.string().uuid().nullable().optional(),
  desconto: decimalString.default('0.00'),
  observacao: z.string().optional(),
  itens: z.array(ItemPedidoRequestSchema).min(1, 'Adicione ao menos um item'),
  pagamentos: z.array(PagamentoRequestSchema).min(1, 'Informe ao menos uma forma de pagamento'),
})
export type CriarPedidoDTO = z.infer<typeof CriarPedidoSchema>

// ── Responses ──
export const ItemPedidoResponseSchema = z.object({
  id: z.string(),
  variante_id: z.string(),
  sku: z.string(),
  quantidade: z.number(),
  preco_unitario: z.string(),
  desconto_item: z.string(),
  subtotal: z.string(),
})
export type ItemPedidoResponse = z.infer<typeof ItemPedidoResponseSchema>

export const PagamentoResponseSchema = z.object({
  id: z.string(),
  forma_pagamento: FormaPagamentoSchema,
  valor: z.string(),
})
export type PagamentoResponse = z.infer<typeof PagamentoResponseSchema>

export const PedidoResponseSchema = z.object({
  id: z.string(),
  numero: z.string(),
  cliente_id: z.string().nullable().optional(),
  usuario_id: z.string(),
  status: StatusPedidoSchema,
  subtotal: z.string(),
  desconto: z.string(),
  valor_total: z.string(),
  criado_em: z.string(),
  confirmado_em: z.string().nullable().optional(),
})
export type Pedido = z.infer<typeof PedidoResponseSchema>

export const PedidoDetalheResponseSchema = PedidoResponseSchema.extend({
  itens: z.array(ItemPedidoResponseSchema),
  pagamentos: z.array(PagamentoResponseSchema),
})
export type PedidoDetalhe = z.infer<typeof PedidoDetalheResponseSchema>

export const PedidoListResponseSchema = paginatedResponseSchema(PedidoResponseSchema)
export type PedidoListResponse = z.infer<typeof PedidoListResponseSchema>
