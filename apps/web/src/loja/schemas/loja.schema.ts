// Contrato da vitrine pública (API /loja). Espelha apps/api/.../vitrine/infrastructure/api/schemas.py.
// Toda resposta passa por estes schemas antes de chegar à UI — assim um
// desencontro de tipo (ex.: número onde a API manda string) quebra aqui, com
// mensagem clara, e não dentro de um componente.

import { z } from 'zod'

const Dinheiro = z.string().regex(/^\d+\.\d{2}$/, 'Valor monetário inválido')

export const CategoriaLojaSchema = z.object({
  id: z.string(),
  nome: z.string(),
  slug: z.string(),
})
export const CategoriasLojaSchema = z.array(CategoriaLojaSchema)

export const VarianteLojaSchema = z.object({
  id: z.string(),
  sku: z.string(),
  tamanho: z.string(),
  cor: z.string(),
  preco_unitario: Dinheiro,
  preco_cheio: Dinheiro,
  disponivel: z.number().int().nonnegative(),
})

export const ImagemLojaSchema = z.object({
  cor: z.string(),
  url: z.string(),
  principal: z.boolean(),
})

export const ProdutoResumoLojaSchema = z.object({
  id: z.string(),
  nome: z.string(),
  marca: z.string(),
  categoria: z.object({ id: z.string(), nome: z.string() }).nullable(),
  desconto_percentual: Dinheiro.nullable(),
  preco_a_partir_de: Dinheiro,
  imagem_principal_url: z.string().nullable(),
  cores: z.array(z.string()),
})

export const ProdutoDetalheLojaSchema = ProdutoResumoLojaSchema.extend({
  descricao: z.string().nullable(),
  variantes: z.array(VarianteLojaSchema),
  imagens: z.array(ImagemLojaSchema),
})

export const ProdutoListaLojaSchema = z.object({
  data: z.array(ProdutoResumoLojaSchema),
  pagination: z.object({
    total: z.number().int().nonnegative(),
    page: z.number().int().positive(),
    per_page: z.number().int().positive(),
  }),
})

export const ItemPedidoLojaSchema = z.object({
  sku: z.string(),
  descricao: z.string(),
  quantidade: z.number().int().positive(),
  preco_unitario: Dinheiro,
  subtotal: Dinheiro,
})

export const PedidoCheckoutLojaSchema = z.object({
  numero: z.string(),
  status: z.string(),
  subtotal: Dinheiro,
  valor_total: Dinheiro,
  reservado_ate: z.string(),
  itens: z.array(ItemPedidoLojaSchema),
})

export type CategoriaLoja = z.infer<typeof CategoriaLojaSchema>
export type VarianteLoja = z.infer<typeof VarianteLojaSchema>
export type ImagemLoja = z.infer<typeof ImagemLojaSchema>
export type ProdutoResumoLoja = z.infer<typeof ProdutoResumoLojaSchema>
export type ProdutoDetalheLoja = z.infer<typeof ProdutoDetalheLojaSchema>
export type ProdutoListaLoja = z.infer<typeof ProdutoListaLojaSchema>
export type PedidoCheckoutLoja = z.infer<typeof PedidoCheckoutLojaSchema>

export type CheckoutLojaRequest = {
  cliente: { nome: string; telefone: string }
  observacao?: string
  itens: { variante_id: string; quantidade: number }[]
}
