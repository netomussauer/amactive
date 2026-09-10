export type { Fornecedor, FornecedorListResponse, CriarFornecedorDTO } from '../schemas/fornecedor.schema'

export type FornecedorFilter = {
  page?: number
  per_page?: number
  busca?: string
}
