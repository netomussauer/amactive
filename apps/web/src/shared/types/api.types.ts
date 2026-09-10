// Tipos alinhados ao docs/openapi.yaml — components.schemas.ProblemDetails
export type ProblemDetails = {
  type?: string
  title?: string
  status?: number
  detail?: string
  instance?: string
}

// components.schemas.PapelUsuario / UsuarioResponse — usado pelo AuthGuard e
// pela sidebar para exibir o usuário logado.
export const PapelUsuario = {
  ADMIN: 'ADMIN',
  VENDEDOR: 'VENDEDOR',
  ESTOQUISTA: 'ESTOQUISTA',
} as const
export type PapelUsuario = (typeof PapelUsuario)[keyof typeof PapelUsuario]

export type Usuario = {
  id: string
  nome: string
  email: string
  papel: PapelUsuario
}
