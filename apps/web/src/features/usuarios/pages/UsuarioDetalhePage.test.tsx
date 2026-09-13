import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { UsuarioDetalhePage } from './UsuarioDetalhePage'
import { ApiError } from '@/shared/lib/api-client'
import { createTestQueryClient } from '@/shared/test-utils/render'
import type { UsuarioDetalhe } from '../types/usuario.types'

const usuarioAdmin: UsuarioDetalhe = {
  id: 'usuario-1',
  nome: 'Ana Souza',
  email: 'ana@amactive.dev',
  papel: 'ADMIN',
  ativo: true,
  criado_em: '2026-01-01T00:00:00Z',
}

let mockUsuario: UsuarioDetalhe | undefined = usuarioAdmin
let mockIsLoading = false

vi.mock('../hooks/useUsuario', () => ({
  useUsuario: () => ({ data: mockUsuario, isLoading: mockIsLoading }),
}))

const atualizarMock = vi.fn()
let atualizarError: unknown = null
vi.mock('../hooks/useAtualizarUsuario', () => ({
  useAtualizarUsuario: () => ({ mutate: atualizarMock, isPending: false, error: atualizarError }),
}))

const inativarMock = vi.fn()
let inativarError: unknown = null
vi.mock('../hooks/useInativarUsuario', () => ({
  useInativarUsuario: () => ({ mutate: inativarMock, error: inativarError }),
}))

const reativarMock = vi.fn()
vi.mock('../hooks/useReativarUsuario', () => ({
  useReativarUsuario: () => ({ mutate: reativarMock, error: null }),
}))

// RedefinirSenhaModal usa a mutation real de useRedefinirSenhaUsuario (não
// mockada aqui — não faz parte do escopo dos testes de 409), então o
// QueryClientProvider precisa estar presente mesmo com o modal fechado.
function renderPage() {
  const queryClient = createTestQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/usuarios/usuario-1']}>
        <Routes>
          <Route path="/usuarios/:usuarioId" element={<UsuarioDetalhePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

// Fluxo crítico: a salvaguarda do backend contra desativar/rebaixar o
// último ADMIN ativo do sistema precisa aparecer de forma clara na tela
// (ver docs/openapi.yaml, respostas 409 de PUT/DELETE /usuarios/{id}).
describe('UsuarioDetalhePage', () => {
  beforeEach(() => {
    window.confirm = vi.fn(() => true)
  })

  afterEach(() => {
    vi.clearAllMocks()
    mockUsuario = usuarioAdmin
    mockIsLoading = false
    atualizarError = null
    inativarError = null
  })

  it('renderiza os dados do usuário e o formulário de edição pré-preenchido', () => {
    renderPage()

    expect(screen.getByRole('heading', { name: 'Ana Souza' })).toBeInTheDocument()
    expect(screen.getByText('ana@amactive.dev')).toBeInTheDocument()
    expect(screen.getByLabelText(/nome completo/i)).toHaveValue('Ana Souza')
    expect(screen.getByLabelText(/^papel/i)).toHaveValue('ADMIN')
    expect(screen.getByText('Ativo')).toBeInTheDocument()
  })

  it('pede confirmação e chama a desativação ao clicar em "Desativar"', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Desativar' }))

    expect(window.confirm).toHaveBeenCalledWith('Desativar o usuário Ana Souza?')
    expect(inativarMock).toHaveBeenCalledWith('usuario-1')
  })

  it('exibe a mensagem amigável do 409 quando o backend recusa desativar o último ADMIN ativo', () => {
    inativarError = new ApiError(
      'Conflito',
      409,
      'Não é possível desativar o único administrador ativo do sistema.',
    )

    renderPage()

    expect(
      screen.getByText(/não é possível desativar o único administrador ativo do sistema/i),
    ).toBeInTheDocument()
  })

  it('exibe a mensagem amigável do 409 quando o backend recusa rebaixar o próprio papel de ADMIN', () => {
    atualizarError = new ApiError(
      'Conflito',
      409,
      'Não é possível remover o papel de ADMIN do único administrador ativo do sistema.',
    )

    renderPage()

    expect(
      screen.getByText(/não é possível remover o papel de admin do único administrador ativo/i),
    ).toBeInTheDocument()
  })

  it('reativa um usuário inativo reenviando nome e papel atuais', async () => {
    mockUsuario = { ...usuarioAdmin, ativo: false }
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Reativar' }))

    expect(reativarMock).toHaveBeenCalledWith({ id: 'usuario-1', nome: 'Ana Souza', papel: 'ADMIN' })
  })

  it('abre o modal de redefinir senha e deixa claro que é um reset administrativo imediato', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: /redefinir senha/i }))

    expect(screen.getByRole('dialog', { name: /redefinir senha de ana souza/i })).toBeInTheDocument()
    expect(screen.getByText(/reset administrativo imediato/i)).toBeInTheDocument()
    expect(screen.getByText(/não é o fluxo de "esqueci minha senha"/i)).toBeInTheDocument()
  })

  it('exibe estado de "usuário não encontrado" quando não há dados', () => {
    mockUsuario = undefined
    renderPage()

    expect(screen.getByText(/usuário não encontrado/i)).toBeInTheDocument()
  })
})
