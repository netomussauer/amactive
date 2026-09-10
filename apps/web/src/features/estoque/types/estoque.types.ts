export type {
  EstoqueItem,
  EstoqueListResponse,
  Movimentacao,
  MovimentacaoListResponse,
  CriarMovimentacaoDTO,
  TipoMovimentacao,
  MotivoMovimentacao,
} from '../schemas/movimentacao.schema'

export type EstoqueFilter = {
  page?: number
  per_page?: number
  sku?: string
}

export type MovimentacaoFilter = {
  page?: number
  per_page?: number
  variante_id?: string
  tipo?: string
}
