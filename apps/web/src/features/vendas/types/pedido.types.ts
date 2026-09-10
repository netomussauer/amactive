export type {
  Pedido,
  PedidoDetalhe,
  PedidoListResponse,
  CriarPedidoDTO,
  ItemPedidoRequest,
  PagamentoRequest,
  StatusPedido,
  FormaPagamento,
} from '../schemas/pedido.schema'

export type PedidoFilter = {
  page?: number
  per_page?: number
  status?: string
  cliente_id?: string
  data_inicio?: string
  data_fim?: string
}

// Item de carrinho — estado local (Zustand) antes da confirmação da venda,
// não existe no servidor até o POST /pedidos. Guarda os dados da variante
// necessários para exibir o carrinho sem precisar buscá-la de novo.
export type CarrinhoItem = {
  varianteId: string
  sku: string
  produtoNome: string
  tamanho: string
  cor: string
  precoUnitario: string
  quantidade: number
  descontoItem: string
  estoqueDisponivel: number
}
