import { z } from 'zod'
import { paginatedResponseSchema } from '@/shared/types/common.types'
import { PapelUsuario } from '@/shared/types/api.types'

const PapelUsuarioSchema = z.enum([PapelUsuario.ADMIN, PapelUsuario.VENDEDOR, PapelUsuario.ESTOQUISTA])

// Espelha CriarUsuarioRequest (docs/openapi.yaml). minLength: 8 na senha
// mantém a mesma convenção já usada em auth/schemas/auth.schema.ts (login).
export const CriarUsuarioSchema = z.object({
  nome: z.string().min(2, 'Informe o nome').max(150),
  email: z.string().min(1, 'Informe o e-mail').email('E-mail inválido'),
  senha: z.string().min(8, 'A senha deve ter pelo menos 8 caracteres'),
  papel: PapelUsuarioSchema,
})
export type CriarUsuarioDTO = z.infer<typeof CriarUsuarioSchema>

// Campos editáveis no formulário de edição (UsuarioEditForm). `ativo` não é
// um campo do formulário — é controlado pela ação de desativar/reativar
// (ver UsuarioDetalhePage/UsuarioTable) — mas a API exige os três campos em
// PUT /usuarios/{id} (ver AtualizarUsuarioRequest), então o chamador
// reenvia o `ativo` atual junto com os valores deste schema.
export const AtualizarUsuarioFormSchema = z.object({
  nome: z.string().min(2, 'Informe o nome').max(150),
  papel: PapelUsuarioSchema,
})
export type AtualizarUsuarioFormValues = z.infer<typeof AtualizarUsuarioFormSchema>

export const AtualizarUsuarioSchema = AtualizarUsuarioFormSchema.extend({
  ativo: z.boolean(),
})
export type AtualizarUsuarioDTO = z.infer<typeof AtualizarUsuarioSchema>

// PATCH /usuarios/{id}/senha — reset administrativo direto (não é o fluxo
// de "esqueci minha senha"; sem e-mail, sem senha atual).
export const RedefinirSenhaSchema = z.object({
  senha: z.string().min(8, 'A senha deve ter pelo menos 8 caracteres'),
})
export type RedefinirSenhaDTO = z.infer<typeof RedefinirSenhaSchema>

// UsuarioDetalheResponse — nunca inclui senha_hash.
export const UsuarioDetalheResponseSchema = z.object({
  id: z.string(),
  nome: z.string(),
  email: z.string(),
  papel: PapelUsuarioSchema,
  ativo: z.boolean(),
  criado_em: z.string(),
})
export type UsuarioDetalhe = z.infer<typeof UsuarioDetalheResponseSchema>

export const UsuarioListResponseSchema = paginatedResponseSchema(UsuarioDetalheResponseSchema)
export type UsuarioListResponse = z.infer<typeof UsuarioListResponseSchema>
