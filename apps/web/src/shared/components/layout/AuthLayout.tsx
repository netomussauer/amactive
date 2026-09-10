import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

// Shell autenticado: Sidebar + Header + <Outlet /> das páginas de feature.
// Renderizado dentro de AuthGuard (app/AuthGuard.tsx).
export function AuthLayout() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-bg-subtle">
      <Sidebar mobileOpen={mobileNavOpen} onCloseMobile={() => setMobileNavOpen(false)} />
      <div className="flex min-h-screen flex-1 flex-col">
        <Header onToggleMobileNav={() => setMobileNavOpen((open) => !open)} />
        <Outlet />
      </div>
    </div>
  )
}
