import { afterEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { RoleGuard } from './RoleGuard'
import { useAuth } from '@/shared/hooks/useAuth'

function renderWithGuard() {
  return render(
    <MemoryRouter initialEntries={['/vendas/pdv']}>
      <Routes>
        <Route path="/produtos" element={<p>Lista de produtos</p>} />
        <Route
          path="/vendas/pdv"
          element={
            <RoleGuard permissao="podeVenderNoPdv">
              <p>Tela do PDV</p>
            </RoleGuard>
          }
        />
      </Routes>
    </MemoryRouter>,
  )
}

describe('RoleGuard', () => {
  afterEach(() => {
    useAuth.setState({ user: null, isAuthenticated: false })
  })

  it('renderiza o conteúdo quando o papel tem a permissão exigida', () => {
    useAuth.setState({
      user: { id: '1', nome: 'Vendedora', email: 'vendedora@amactive.dev', papel: 'VENDEDOR' },
      isAuthenticated: true,
    })

    renderWithGuard()
    expect(screen.getByText('Tela do PDV')).toBeInTheDocument()
  })

  it('redireciona para a primeira rota permitida quando o papel não tem a permissão exigida', () => {
    useAuth.setState({
      user: { id: '1', nome: 'Estoquista', email: 'estoquista@amactive.dev', papel: 'ESTOQUISTA' },
      isAuthenticated: true,
    })

    renderWithGuard()
    expect(screen.queryByText('Tela do PDV')).not.toBeInTheDocument()
    expect(screen.getByText('Lista de produtos')).toBeInTheDocument()
  })
})
