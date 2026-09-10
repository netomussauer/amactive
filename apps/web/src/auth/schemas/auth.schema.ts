import { z } from 'zod'
import { PapelUsuario } from '@/shared/types/api.types'

// Espelha components.schemas.LoginRequest / LoginResponse (docs/openapi.yaml)
export const LoginFormSchema = z.object({
  email: z.string().min(1, 'Informe o e-mail').email('E-mail inválido'),
  senha: z.string().min(8, 'A senha deve ter pelo menos 8 caracteres'),
})
export type LoginFormValues = z.infer<typeof LoginFormSchema>

export const UsuarioResponseSchema = z.object({
  id: z.string(),
  nome: z.string(),
  email: z.string(),
  papel: z.enum([PapelUsuario.ADMIN, PapelUsuario.VENDEDOR, PapelUsuario.ESTOQUISTA]),
})

export const LoginResponseSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  usuario: UsuarioResponseSchema,
})
export type LoginResponse = z.infer<typeof LoginResponseSchema>
