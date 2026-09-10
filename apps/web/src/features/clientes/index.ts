// Barrel export público da feature "clientes".
// Exponha aqui apenas o que outras features/rotas precisam consumir
// (hooks, tipos). Nunca componentes internos.
export { useClientes } from './hooks/useClientes'
export type { Cliente } from './types/cliente.types'
