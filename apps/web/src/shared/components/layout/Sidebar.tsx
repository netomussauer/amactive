import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Shirt,
  Boxes,
  ShoppingCart,
  Receipt,
  Users,
  Truck,
  BarChart3,
  X,
} from 'lucide-react'
import { routes } from '@/shared/lib/routes'
import { cn } from '@/shared/lib/utils'
import { usePermissoes } from '@/shared/hooks/usePermissoes'
import type { Permissoes } from '@/shared/lib/permissoes'

// `permissao` ausente = leitura livre aos três papéis (Pedidos, Produtos,
// Estoque) — o item some apenas quando o papel não tem NENHUM acesso ao
// recurso. Ver shared/lib/permissoes.ts para o racional de cada flag e
// app/router.tsx para o guard de rota correspondente.
const navItems: Array<{ to: string; label: string; icon: typeof LayoutDashboard; permissao?: keyof Permissoes }> = [
  { to: routes.dashboard, label: 'Dashboard', icon: LayoutDashboard, permissao: 'podeVerRelatorios' },
  { to: routes.pdv, label: 'PDV', icon: ShoppingCart, permissao: 'podeVenderNoPdv' },
  { to: routes.pedidos, label: 'Pedidos', icon: Receipt },
  { to: routes.produtos, label: 'Produtos', icon: Shirt },
  { to: routes.estoque, label: 'Estoque', icon: Boxes },
  { to: routes.clientes, label: 'Clientes', icon: Users, permissao: 'podeGerenciarClientes' },
  { to: routes.fornecedores, label: 'Fornecedores', icon: Truck, permissao: 'podeGerenciarFornecedores' },
  { to: routes.relatorios, label: 'Relatórios', icon: BarChart3, permissao: 'podeVerRelatorios' },
]

type Props = {
  mobileOpen?: boolean
  onCloseMobile?: () => void
}

export function Sidebar({ mobileOpen = false, onCloseMobile }: Props) {
  const permissoes = usePermissoes()
  const itensVisiveis = navItems.filter((item) => !item.permissao || permissoes[item.permissao])

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}
      <nav
        aria-label="Navegação principal"
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-60 shrink-0 -translate-x-full flex-col border-r border-border bg-bg transition-transform',
          'md:static md:z-auto md:translate-x-0',
          mobileOpen && 'translate-x-0',
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-border px-6">
          <span className="font-sans text-xl font-bold tracking-tight text-primary">AMACTIVE</span>
          <button
            type="button"
            aria-label="Fechar menu"
            className="text-text-muted md:hidden"
            onClick={onCloseMobile}
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>
        <ul className="flex-1 space-y-1 overflow-y-auto p-3">
          {itensVisiveis.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-md px-3 py-2.5 text-sm font-medium text-text-muted transition-colors',
                    'hover:bg-bg-subtle hover:text-text',
                    isActive && 'bg-primary-subtle text-primary hover:bg-primary-subtle hover:text-primary',
                  )
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </>
  )
}
