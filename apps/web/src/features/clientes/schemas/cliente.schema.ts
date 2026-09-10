import { z } from 'zod'
import { paginatedResponseSchema } from '@/shared/types/common.types'

export const CriarClienteSchema = z.object({
  nome: z.string().min(2, 'Informe o nome').max(150),
  cpf_cnpj: z.string().max(20).optional().or(z.literal('')),
  email: z.string().email('E-mail inválido').optional().or(z.literal('')),
  telefone: z.string().max(20).optional().or(z.literal('')),
  endereco_logradouro: z.string().max(200).optional().or(z.literal('')),
  endereco_cidade: z.string().max(100).optional().or(z.literal('')),
  endereco_uf: z.string().length(2, 'UF deve ter 2 letras').optional().or(z.literal('')),
  endereco_cep: z.string().max(10).optional().or(z.literal('')),
})
export type CriarClienteDTO = z.infer<typeof CriarClienteSchema>

export const ClienteResponseSchema = CriarClienteSchema.extend({
  id: z.string(),
  ativo: z.boolean(),
  criado_em: z.string(),
})
export type Cliente = z.infer<typeof ClienteResponseSchema>

export const ClienteListResponseSchema = paginatedResponseSchema(ClienteResponseSchema)
export type ClienteListResponse = z.infer<typeof ClienteListResponseSchema>
