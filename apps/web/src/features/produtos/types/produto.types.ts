export type {
  Produto,
  ProdutoDetalhe,
  ProdutoListResponse,
  Variante,
  VarianteListResponse,
  Categoria,
  CriarProdutoDTO,
  AtualizarProdutoDTO,
  CriarVarianteDTO,
  AtualizarVarianteDTO,
  Tamanho,
} from '../schemas/produto.schema'

export type ProdutoFilter = {
  page?: number
  per_page?: number
  busca?: string
  categoria_id?: string
  ativo?: boolean
}
