export type {
  UsuarioDetalhe,
  UsuarioListResponse,
  CriarUsuarioDTO,
  AtualizarUsuarioFormValues,
  AtualizarUsuarioDTO,
  RedefinirSenhaDTO,
} from '../schemas/usuario.schema'

// GET /usuarios só aceita paginação (ver docs/openapi.yaml) — sem busca
// textual, diferente de clientes/fornecedores.
export type UsuarioFilter = {
  page?: number
  per_page?: number
}
