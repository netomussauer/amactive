import { z } from 'zod'

export const ProdutoMaisVendidoSchema = z.object({
  variante_id: z.string(),
  sku: z.string(),
  produto_nome: z.string(),
  quantidade_vendida: z.number(),
  faturamento: z.string(),
})
export type ProdutoMaisVendido = z.infer<typeof ProdutoMaisVendidoSchema>

export const DashboardResumoResponseSchema = z.object({
  faturamento_periodo: z.string(),
  total_pedidos_periodo: z.number(),
  ticket_medio: z.string(),
  variantes_em_alerta_estoque: z.number(),
  top_produtos: z.array(ProdutoMaisVendidoSchema),
})
export type DashboardResumo = z.infer<typeof DashboardResumoResponseSchema>
