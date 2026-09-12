export type {
  Produto,
  ProdutoDetalhe,
  ProdutoListResponse,
  Variante,
  VarianteListResponse,
  Categoria,
  CategoriaListResponse,
  CriarProdutoDTO,
  AtualizarProdutoDTO,
  CriarVarianteDTO,
  AtualizarVarianteDTO,
  CriarCategoriaDTO,
  Tamanho,
} from '../schemas/produto.schema'

export type ProdutoFilter = {
  page?: number
  per_page?: number
  busca?: string
  categoria_id?: string
  ativo?: boolean
}
