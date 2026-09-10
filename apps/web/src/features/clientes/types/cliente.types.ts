export type { Cliente, ClienteListResponse, CriarClienteDTO } from '../schemas/cliente.schema'

export type ClienteFilter = {
  page?: number
  per_page?: number
  busca?: string
}
