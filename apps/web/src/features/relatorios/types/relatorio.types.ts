export type { VendaPorDia, ProdutoMaisVendido, GiroEstoqueItem } from '../schemas/relatorio.schema'

export type PeriodoFilter = {
  data_inicio?: string
  data_fim?: string
}

// Vendas por período: além do período (obrigatório), aceita filtro opcional de
// canal de origem (PDV | WHATSAPP | NUVEMSHOP). Vazio/undefined = todos.
export type VendasPorPeriodoFilter = Required<PeriodoFilter> & {
  origem_canal?: string
}
