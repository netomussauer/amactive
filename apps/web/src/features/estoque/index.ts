// Barrel export público da feature "estoque".
// Exponha aqui apenas o que outras features/rotas precisam consumir
// (hooks, tipos). Nunca componentes internos.
export { useAlertasEstoque } from './hooks/useAlertasEstoque'
export type { EstoqueItem } from './types/estoque.types'
