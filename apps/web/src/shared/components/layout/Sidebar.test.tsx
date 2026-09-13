import { afterEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { axe, toHaveNoViolations } from 'jest-axe'
import { Sidebar } from './Sidebar'
import { useAuth } from '@/shared/hooks/useAuth'
import type { Usuario } from '@/shared/types/api.types'

expect.extend(toHaveNoViolations)

function login(papel: Usuario['papel']) {
  useAuth.setState({
    user: { id: '1', nome: 'Usuário Teste', email: 'teste@amactive.dev', papel },
    isAuthenticated: true,
  })
}

function renderSidebar() {
  return render(
    <MemoryRouter>
      <Sidebar />
    </MemoryRouter>,
  )
}

describe('Sidebar', () => {
  afterEach(() => {
    useAuth.setState({ user: null, isAuthenticated: false })
  })

  it('ADMIN vê todos os itens de navegação', () => {
    login('ADMIN')
    renderSidebar()

    for (const label of [
      'Dashboard',
      'PDV',
      'Pedidos',
      'Produtos',
      'Estoque',
      'Clientes',
      'Fornecedores',
      'Relatórios',
      'Usuários',
    ]) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    }
  })

  it('VENDEDOR não vê Dashboard, Fornecedores, Relatórios nem Usuários', () => {
    login('VENDEDOR')
    renderSidebar()

    for (const label of ['PDV', 'Pedidos', 'Produtos', 'Estoque', 'Clientes']) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    }
    for (const label of ['Dashboard', 'Fornecedores', 'Relatórios', 'Usuários']) {
      expect(screen.queryByRole('link', { name: label })).not.toBeInTheDocument()
    }
  })

  it('ESTOQUISTA não vê Dashboard, PDV, Clientes, Relatórios nem Usuários', () => {
    login('ESTOQUISTA')
    renderSidebar()

    for (const label of ['Pedidos', 'Produtos', 'Estoque', 'Fornecedores']) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    }
    for (const label of ['Dashboard', 'PDV', 'Clientes', 'Relatórios', 'Usuários']) {
      expect(screen.queryByRole('link', { name: label })).not.toBeInTheDocument()
    }
  })

  it('sem violações de acessibilidade', async () => {
    login('ADMIN')
    const { container } = renderSidebar()
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
