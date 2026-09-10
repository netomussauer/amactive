// Constantes de rota — única fonte de verdade para path strings, usada tanto
// pelo router quanto pela Sidebar/links internos. Ver docs/frontend-architecture.md §4.1.
export const routes = {
  login: '/login',
  dashboard: '/dashboard',
  produtos: '/produtos',
  produtoNovo: '/produtos/novo',
  produtoDetalhe: (id: string) => `/produtos/${id}`,
  estoque: '/estoque',
  estoqueMovimentacoes: '/estoque/movimentacoes',
  pdv: '/vendas/pdv',
  pedidos: '/vendas/pedidos',
  pedidoDetalhe: (id: string) => `/vendas/pedidos/${id}`,
  clientes: '/clientes',
  clienteNovo: '/clientes/novo',
  clienteDetalhe: (id: string) => `/clientes/${id}`,
  fornecedores: '/fornecedores',
  fornecedorNovo: '/fornecedores/novo',
  fornecedorDetalhe: (id: string) => `/fornecedores/${id}`,
  relatorios: '/relatorios',
} as const
