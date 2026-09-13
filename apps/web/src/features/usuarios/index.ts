// Barrel export público da feature "usuarios".
// Exponha aqui apenas o que outras features/rotas precisam consumir
// (hooks, tipos). Nunca componentes internos.
export { useUsuarios } from './hooks/useUsuarios'
export type { UsuarioDetalhe } from './types/usuario.types'
