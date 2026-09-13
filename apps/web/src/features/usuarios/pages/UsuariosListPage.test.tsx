import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { axe, toHaveNoViolations } from 'jest-axe'
import { UsuariosListPage } from './UsuariosListPage'
import type { UsuarioDetalhe } from '../types/usuario.types'

expect.extend(toHaveNoViolations)

const usuarios: UsuarioDetalhe[] = [
  { id: 'usuario-1', nome: 'Ana Souza', email: 'ana@amactive.dev', papel: 'ADMIN', ativo: true, criado_em: '2026-01-01T00:00:00Z' },
  { id: 'usuario-2', nome: 'Beto Lima', email: 'beto@amactive.dev', papel: 'ESTOQUISTA', ativo: false, criado_em: '2026-01-02T00:00:00Z' },
]

let mockData: { data: UsuarioDetalhe[]; pagination: { total: number; page: number; per_page: number } } | undefined = {
  data: usuarios,
  pagination: { total: 2, page: 1, per_page: 20 },
}
let mockIsLoading = false

vi.mock('../hooks/useUsuarios', () => ({
  useUsuarios: () => ({ data: mockData, isLoading: mockIsLoading }),
}))

const inativarMock = vi.fn()
const reativarMock = vi.fn()
vi.mock('../hooks/useInativarUsuario', () => ({
  useInativarUsuario: () => ({ mutate: inativarMock }),
}))
vi.mock('../hooks/useReativarUsuario', () => ({
  useReativarUsuario: () => ({ mutate: reativarMock }),
}))

function renderPage() {
  return render(
    <MemoryRouter>
      <UsuariosListPage />
    </MemoryRouter>,
  )
}

describe('UsuariosListPage', () => {
  afterEach(() => {
    vi.clearAllMocks()
    mockData = { data: usuarios, pagination: { total: 2, page: 1, per_page: 20 } }
    mockIsLoading = false
  })

  it('lista os usuários cadastrados com nome, e-mail, papel e status', () => {
    renderPage()

    expect(screen.getByText('Ana Souza')).toBeInTheDocument()
    expect(screen.getByText('ana@amactive.dev')).toBeInTheDocument()
    expect(screen.getByText('Administrador(a)')).toBeInTheDocument()
    expect(screen.getByText('Ativo')).toBeInTheDocument()

    expect(screen.getByText('Beto Lima')).toBeInTheDocument()
    expect(screen.getByText('Estoquista')).toBeInTheDocument()
    expect(screen.getByText('Inativo')).toBeInTheDocument()
  })

  it('exibe o botão "Desativar" para usuário ativo e "Reativar" para usuário inativo', () => {
    renderPage()

    const linhaAtiva = screen.getByText('Ana Souza').closest('tr') as HTMLElement
    const linhaInativa = screen.getByText('Beto Lima').closest('tr') as HTMLElement

    expect(within(linhaAtiva).getByRole('button', { name: 'Desativar' })).toBeInTheDocument()
    expect(within(linhaInativa).getByRole('button', { name: 'Reativar' })).toBeInTheDocument()
  })

  it('exibe estado vazio quando não há usuários cadastrados', () => {
    mockData = { data: [], pagination: { total: 0, page: 1, per_page: 20 } }
    renderPage()

    expect(screen.getByText(/nenhum usuário cadastrado ainda/i)).toBeInTheDocument()
  })

  it('exibe o botão "Novo usuário"', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /novo usuário/i })).toBeInTheDocument()
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = renderPage()
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
