import { z } from 'zod'
import { paginatedResponseSchema } from '@/shared/types/common.types'

export const CriarFornecedorSchema = z.object({
  razao_social: z.string().min(2, 'Informe a razão social').max(150),
  nome_fantasia: z.string().max(150).optional().or(z.literal('')),
  cnpj: z.string().max(20).optional().or(z.literal('')),
  email: z.string().email('E-mail inválido').optional().or(z.literal('')),
  telefone: z.string().max(20).optional().or(z.literal('')),
  endereco_logradouro: z.string().max(200).optional().or(z.literal('')),
  endereco_cidade: z.string().max(100).optional().or(z.literal('')),
  endereco_uf: z.string().length(2, 'UF deve ter 2 letras').optional().or(z.literal('')),
  endereco_cep: z.string().max(10).optional().or(z.literal('')),
})
export type CriarFornecedorDTO = z.infer<typeof CriarFornecedorSchema>

export const FornecedorResponseSchema = CriarFornecedorSchema.extend({
  id: z.string(),
  ativo: z.boolean(),
  criado_em: z.string(),
})
export type Fornecedor = z.infer<typeof FornecedorResponseSchema>

export const FornecedorListResponseSchema = paginatedResponseSchema(FornecedorResponseSchema)
export type FornecedorListResponse = z.infer<typeof FornecedorListResponseSchema>
