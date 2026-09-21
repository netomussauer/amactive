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

// NUVEMSHOP = "pago externamente pelo checkout do canal" — só faz sentido em
// pedidos de origem NUVEMSHOP (regra de UI; o backend não amarra forma a canal).
export const FormaPagamento = {
  DINHEIRO: 'DINHEIRO',
  PIX: 'PIX',
  CARTAO_DEBITO: 'CARTAO_DEBITO',
  CARTAO_CREDITO: 'CARTAO_CREDITO',
  NUVEMSHOP: 'NUVEMSHOP',
} as const
export const FormaPagamentoSchema = z.enum(['DINHEIRO', 'PIX', 'CARTAO_DEBITO', 'CARTAO_CREDITO', 'NUVEMSHOP'])
export type FormaPagamento = z.infer<typeof FormaPagamentoSchema>

// Canal de origem do pedido (registrado manualmente pelo operador).
export const OrigemCanal = {
  PDV: 'PDV',
  WHATSAPP: 'WHATSAPP',
  NUVEMSHOP: 'NUVEMSHOP',
} as const
export const OrigemCanalSchema = z.enum(['PDV', 'WHATSAPP', 'NUVEMSHOP'])
export type OrigemCanal = z.infer<typeof OrigemCanalSchema>

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

// Número do pedido na Nuvemshop (único canal que usa): 1..100 caracteres.
export const PedidoExternoIdSchema = z
  .string()
  .trim()
  .min(1, 'Informe o número do pedido')
  .max(100, 'Máximo de 100 caracteres')

// Regras por canal (espelham o backend): NUVEMSHOP exige pedido_externo_id,
// PDV e WHATSAPP o rejeitam (422 no backend — há índice único
// (origem_canal, pedido_externo_id), então uma "referência" de WhatsApp como
// nome/telefone daria 409 na 2ª compra da mesma cliente). Compartilhada com o
// formulário do PDV para exibir o mesmo erro inline antes do POST.
export function validarOrigemCanal(
  data: { origem_canal: OrigemCanal; pedido_externo_id?: string | null },
  ctx: z.RefinementCtx,
): void {
  const temNumero = Boolean(data.pedido_externo_id?.trim())
  if (data.origem_canal === 'NUVEMSHOP' && !temNumero) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['pedido_externo_id'],
      message: 'Informe o número do pedido na Nuvemshop',
    })
  }
  if (data.origem_canal !== 'NUVEMSHOP' && temNumero) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['pedido_externo_id'],
      message: 'Apenas pedidos da Nuvemshop têm número de pedido externo',
    })
  }
}

export const CriarPedidoSchema = z
  .object({
    cliente_id: z.string().uuid().nullable().optional(),
    origem_canal: OrigemCanalSchema.default('PDV'),
    pedido_externo_id: PedidoExternoIdSchema.optional(),
    desconto: decimalString.default('0.00'),
    observacao: z.string().optional(),
    itens: z.array(ItemPedidoRequestSchema).min(1, 'Adicione ao menos um item'),
    pagamentos: z.array(PagamentoRequestSchema).min(1, 'Informe ao menos uma forma de pagamento'),
  })
  .superRefine(validarOrigemCanal)
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
  // string (não enum) na resposta: um canal novo no backend não deve quebrar a listagem.
  origem_canal: z.string(),
  pedido_externo_id: z.string().nullable().optional(),
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
