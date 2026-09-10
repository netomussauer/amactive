import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthGuard } from './AuthGuard'
import { useAuth } from '@/shared/hooks/useAuth'

function renderWithGuard(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<p>Tela de login</p>} />
        <Route
          path="/dashboard"
          element={
            <AuthGuard>
              <p>Conteúdo protegido</p>
            </AuthGuard>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

// Testes do guard de rota autenticada.
describe('AuthGuard', () => {
  beforeEach(() => {
    useAuth.setState({ user: null, isAuthenticated: false })
  })

  afterEach(() => {
    useAuth.setState({ user: null, isAuthenticated: false })
  })

  it('redireciona para /login quando o usuário não está autenticado', () => {
    renderWithGuard('/dashboard')
    expect(screen.getByText('Tela de login')).toBeInTheDocument()
  })

  it('renderiza o conteúdo protegido quando o usuário está autenticado', () => {
    useAuth.setState({
      user: { id: '1', nome: 'Admin', email: 'admin@amactive.dev', papel: 'ADMIN' },
      isAuthenticated: true,
    })

    renderWithGuard('/dashboard')
    expect(screen.getByText('Conteúdo protegido')).toBeInTheDocument()
  })

  it('derruba a sessão ao receber o evento global de não autorizado (401)', () => {
    useAuth.setState({
      user: { id: '1', nome: 'Admin', email: 'admin@amactive.dev', papel: 'ADMIN' },
      isAuthenticated: true,
    })

    renderWithGuard('/dashboard')
    expect(screen.getByText('Conteúdo protegido')).toBeInTheDocument()

    act(() => {
      window.dispatchEvent(new CustomEvent('amactive:unauthorized'))
    })

    expect(screen.getByText('Tela de login')).toBeInTheDocument()
  })
})
