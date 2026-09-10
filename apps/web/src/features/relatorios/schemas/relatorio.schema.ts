import { z } from 'zod'
import { listResponseSchema } from '@/shared/types/common.types'

export const VendaPorDiaSchema = z.object({
  dia: z.string(),
  total_pedidos: z.number(),
  faturamento: z.string(),
})
export type VendaPorDia = z.infer<typeof VendaPorDiaSchema>
export const VendasPorPeriodoResponseSchema = listResponseSchema(VendaPorDiaSchema)

export const ProdutoMaisVendidoSchema = z.object({
  variante_id: z.string(),
  sku: z.string(),
  produto_nome: z.string(),
  quantidade_vendida: z.number(),
  faturamento: z.string(),
})
export type ProdutoMaisVendido = z.infer<typeof ProdutoMaisVendidoSchema>
export const ProdutosMaisVendidosResponseSchema = listResponseSchema(ProdutoMaisVendidoSchema)

export const GiroEstoqueItemSchema = z.object({
  variante_id: z.string(),
  sku: z.string(),
  total_saidas: z.number(),
  saldo_atual: z.number(),
})
export type GiroEstoqueItem = z.infer<typeof GiroEstoqueItemSchema>
export const GiroEstoqueResponseSchema = listResponseSchema(GiroEstoqueItemSchema)
