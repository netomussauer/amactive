// Barrel export público da feature "fornecedores".
// Exponha aqui apenas o que outras features/rotas precisam consumir
// (hooks, tipos). Nunca componentes internos.
export { useFornecedores } from './hooks/useFornecedores'
export type { Fornecedor } from './types/fornecedor.types'
