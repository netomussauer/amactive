import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/shared/hooks/useAuth'
import { routes } from '@/shared/lib/routes'

type Props = {
  children: ReactNode
}

// Guard de rota autenticada. Também escuta o evento global disparado pelo
// api-client em respostas 401 (sessão expirada) para derrubar a sessão e
// redirecionar ao login — ver shared/lib/api-client.ts.
export function AuthGuard({ children }: Props) {
  const isAuthenticated = useAuth((state) => state.isAuthenticated)
  const logout = useAuth((state) => state.logout)
  const location = useLocation()

  useEffect(() => {
    function handleUnauthorized() {
      logout()
    }
    window.addEventListener('amactive:unauthorized', handleUnauthorized)
    return () => window.removeEventListener('amactive:unauthorized', handleUnauthorized)
  }, [logout])

  if (!isAuthenticated) {
    return <Navigate to={routes.login} state={{ from: location.pathname }} replace />
  }

  return <>{children}</>
}
