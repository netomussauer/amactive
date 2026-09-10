// Barrel export público da feature "produtos".
// Exponha aqui apenas o que outras features/rotas precisam consumir
// (hooks, tipos). Nunca componentes internos.
export { useProdutoPorSku } from './hooks/useProdutoPorSku'
export { useProdutos } from './hooks/useProdutos'
export { useVariantesDoProduto } from './hooks/useVariantesDoProduto'
export type { Variante, Produto } from './types/produto.types'
