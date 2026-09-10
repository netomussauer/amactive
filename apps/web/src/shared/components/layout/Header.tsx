import { LogOut, Menu } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/shared/hooks/useAuth'
import { routes } from '@/shared/lib/routes'
import { Button } from '@/shared/components/ui/Button'

type Props = {
  onToggleMobileNav?: () => void
}

export function Header({ onToggleMobileNav }: Props) {
  const user = useAuth((state) => state.user)
  const logout = useAuth((state) => state.logout)
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate(routes.login, { replace: true })
  }

  return (
    <header className="flex h-16 items-center justify-between border-b border-border bg-bg px-4 md:px-6">
      <button
        type="button"
        aria-label="Abrir menu de navegação"
        className="text-text md:hidden"
        onClick={onToggleMobileNav}
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </button>
      <span className="hidden font-sans text-lg font-semibold text-text md:block">
        Moda fitness feminina — controle de estoque e vendas
      </span>
      <div className="flex items-center gap-3">
        {user && (
          <div className="text-right leading-tight">
            <p className="text-sm font-medium text-text">{user.nome}</p>
            <p className="text-xs text-text-muted">{user.papel}</p>
          </div>
        )}
        <Button variant="ghost" size="icon" aria-label="Sair" onClick={handleLogout}>
          <LogOut className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </header>
  )
}
