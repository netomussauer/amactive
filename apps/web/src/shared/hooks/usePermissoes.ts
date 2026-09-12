import { useAuth } from './useAuth'
import { getPermissoes, type Permissoes } from '@/shared/lib/permissoes'

// Hook central de RBAC do frontend — deriva as permissões do papel do
// usuário logado (`useAuth`). É o único ponto que componentes devem usar
// para decidir o que mostrar/permitir; ver shared/lib/permissoes.ts para a
// matriz completa e o racional de cada flag.
export function usePermissoes(): Permissoes {
  const papel = useAuth((state) => state.user?.papel)
  return getPermissoes(papel)
}
