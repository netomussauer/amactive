import { z } from 'zod'
import { paginatedResponseSchema, listResponseSchema } from '@/shared/types/common.types'

const decimalString = z.string().regex(/^\d+\.\d{2}$/, 'Formato inválido: use 129.90')

// ── Produto ──
export const CriarProdutoSchema = z.object({
  nome: z.string().min(2, 'Informe o nome do produto').max(200),
  descricao: z.string().max(2000).optional().or(z.literal('')),
  // O <select> de categoria normaliza "" → null via setValueAs no register
  // (ver ProdutoForm) antes de chegar aqui, então null é sempre um valor válido.
  categoria_id: z.string().uuid().nullable().optional(),
  marca: z.string().max(100).default('AMACTIVE'),
})
export type CriarProdutoDTO = z.infer<typeof CriarProdutoSchema>

export const AtualizarProdutoSchema = CriarProdutoSchema.extend({
  ativo: z.boolean().optional(),
})
export type AtualizarProdutoDTO = z.infer<typeof AtualizarProdutoSchema>

export const ProdutoResponseSchema = z.object({
  id: z.string(),
  nome: z.string(),
  descricao: z.string().nullable().optional(),
  categoria_id: z.string().nullable().optional(),
  marca: z.string(),
  ativo: z.boolean(),
  criado_em: z.string(),
})
export type Produto = z.infer<typeof ProdutoResponseSchema>

// ── Variante (SKU) ──
export const TamanhoSchema = z.string().min(1, 'Informe o tamanho')
export type Tamanho = z.infer<typeof TamanhoSchema>

export const CriarVarianteSchema = z.object({
  sku: z.string().optional().or(z.literal('')),
  tamanho: TamanhoSchema,
  cor: z.string().min(1, 'Informe a cor').max(50),
  preco_venda: decimalString,
  preco_custo: decimalString.nullable().optional().or(z.literal('')),
  estoque_inicial: z.number().int().min(0).default(0),
})
export type CriarVarianteDTO = z.infer<typeof CriarVarianteSchema>

export const AtualizarVarianteSchema = z.object({
  cor: z.string().max(50).optional(),
  preco_venda: decimalString.optional(),
  preco_custo: decimalString.nullable().optional(),
  ativo: z.boolean().optional(),
})
export type AtualizarVarianteDTO = z.infer<typeof AtualizarVarianteSchema>

export const VarianteResponseSchema = z.object({
  id: z.string(),
  produto_id: z.string(),
  sku: z.string(),
  tamanho: TamanhoSchema,
  cor: z.string(),
  preco_venda: z.string(),
  preco_custo: z.string().nullable().optional(),
  ativo: z.boolean(),
  quantidade_estoque: z.number(),
})
export type Variante = z.infer<typeof VarianteResponseSchema>

export const ProdutoDetalheResponseSchema = ProdutoResponseSchema.extend({
  variantes: z.array(VarianteResponseSchema),
})
export type ProdutoDetalhe = z.infer<typeof ProdutoDetalheResponseSchema>

export const ProdutoListResponseSchema = paginatedResponseSchema(ProdutoResponseSchema)
export type ProdutoListResponse = z.infer<typeof ProdutoListResponseSchema>

export const VarianteListResponseSchema = listResponseSchema(VarianteResponseSchema)
export type VarianteListResponse = z.infer<typeof VarianteListResponseSchema>

// ── Categoria (usado no filtro/form de produto) ──
export const CategoriaResponseSchema = z.object({
  id: z.string(),
  nome: z.string(),
  slug: z.string(),
  ativo: z.boolean(),
})
export type Categoria = z.infer<typeof CategoriaResponseSchema>

export const CategoriaListResponseSchema = listResponseSchema(CategoriaResponseSchema)
