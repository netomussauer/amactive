import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import { LoginPage } from './LoginPage'
import { useAuth } from '@/shared/hooks/useAuth'

const mutateMock = vi.fn()

vi.mock('../hooks/useLogin', () => ({
  useLogin: () => ({ mutate: mutateMock, isPending: false, error: null }),
}))

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <LoginPage />
    </MemoryRouter>,
  )
}

// Testes da tela de login (validação, submissão e redirecionamento).
describe('LoginPage', () => {
  beforeEach(() => {
    mutateMock.mockClear()
    useAuth.setState({ user: null, isAuthenticated: false })
  })

  afterEach(() => {
    useAuth.setState({ user: null, isAuthenticated: false })
  })

  it('renderiza os campos de e-mail e senha e o botão de entrar', () => {
    renderLoginPage()

    expect(screen.getByLabelText(/e-mail/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/senha/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /entrar/i })).toBeInTheDocument()
  })

  it('exibe erros de validação ao submeter o formulário vazio', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: /entrar/i }))

    expect(await screen.findByText(/informe o e-mail/i)).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it('chama o login com e-mail e senha válidos', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText(/e-mail/i), 'admin@amactive.dev')
    await user.type(screen.getByLabelText(/senha/i), 'amactive123')
    await user.click(screen.getByRole('button', { name: /entrar/i }))

    expect(mutateMock).toHaveBeenCalledWith(
      { email: 'admin@amactive.dev', senha: 'amactive123' },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    )
  })
})
