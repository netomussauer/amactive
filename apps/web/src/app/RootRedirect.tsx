import { Navigate } from 'react-router-dom'
import { useAuth } from '@/shared/hooks/useAuth'
import { primeiraRotaPermitida } from '@/shared/lib/permissoes'

// Redireciona "/" para a primeira rota que o papel do usuário logado
// consegue acessar (ex: ADMIN cai no Dashboard; ESTOQUISTA, que não acessa o
// Dashboard, cai em Produtos). Renderizado dentro do AuthGuard, que já trata
// o caso de usuário deslogado — aqui não é preciso checar autenticação.
export function RootRedirect() {
  const papel = useAuth((state) => state.user?.papel)
  return <Navigate to={primeiraRotaPermitida(papel)} replace />
}
