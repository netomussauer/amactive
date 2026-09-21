// Barrel export público da feature "vendas".
// Exponha aqui apenas o que outras features/rotas precisam consumir
// (hooks, tipos). Nunca componentes internos.
export { ORIGEM_CANAL_OPTIONS, labelCanal } from './lib/canal'
export type { OrigemCanal } from './types/pedido.types'
