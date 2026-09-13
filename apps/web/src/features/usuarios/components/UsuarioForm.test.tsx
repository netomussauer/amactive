import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe, toHaveNoViolations } from 'jest-axe'
import { UsuarioForm } from './UsuarioForm'
import { ApiError } from '@/shared/lib/api-client'
import type { UsuarioDetalhe, CriarUsuarioDTO } from '../types/usuario.types'

expect.extend(toHaveNoViolations)

const usuarioCriado: UsuarioDetalhe = {
  id: 'usuario-1',
  nome: 'Ana Souza',
  email: 'ana@amactive.dev',
  papel: 'VENDEDOR',
  ativo: true,
  criado_em: '2026-01-01T00:00:00Z',
}

type MutateOptions = { onSuccess?: (usuario: UsuarioDetalhe) => void; onError?: (error: unknown) => void }
let shouldFailWith409 = false
const mutateMock = vi.fn((_payload: CriarUsuarioDTO, options?: MutateOptions) => {
  if (shouldFailWith409) {
    options?.onError?.(new ApiError('Conflito', 409, 'E-mail já cadastrado para outro usuário.'))
    return
  }
  options?.onSuccess?.(usuarioCriado)
})

vi.mock('../hooks/useCriarUsuario', () => ({
  useCriarUsuario: () => ({ mutate: mutateMock, isPending: false }),
}))

describe('UsuarioForm', () => {
  afterEach(() => {
    vi.clearAllMocks()
    shouldFailWith409 = false
  })

  it('renderiza os campos de cadastro', () => {
    render(<UsuarioForm onSuccess={vi.fn()} />)

    expect(screen.getByLabelText(/nome completo/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^e-mail/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/senha inicial/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^papel/i)).toBeInTheDocument()
  })

  it('exibe erros de validação ao submeter vazio', async () => {
    const user = userEvent.setup()
    render(<UsuarioForm onSuccess={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: /cadastrar usuário/i }))

    expect(await screen.findByText(/informe o nome/i)).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it('cadastra o usuário com dados válidos e chama onSuccess', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    render(<UsuarioForm onSuccess={onSuccess} />)

    await user.type(screen.getByLabelText(/nome completo/i), 'Ana Souza')
    await user.type(screen.getByLabelText(/^e-mail/i), 'ana@amactive.dev')
    await user.type(screen.getByLabelText(/senha inicial/i), 'senha1234')
    await user.selectOptions(screen.getByLabelText(/^papel/i), 'ADMIN')
    await user.click(screen.getByRole('button', { name: /cadastrar usuário/i }))

    expect(mutateMock).toHaveBeenCalledWith(
      { nome: 'Ana Souza', email: 'ana@amactive.dev', senha: 'senha1234', papel: 'ADMIN' },
      expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) }),
    )
    expect(onSuccess).toHaveBeenCalledWith(usuarioCriado)
  })

  it('exibe o erro 409 de e-mail duplicado no campo de e-mail', async () => {
    shouldFailWith409 = true
    const user = userEvent.setup()
    render(<UsuarioForm onSuccess={vi.fn()} />)

    await user.type(screen.getByLabelText(/nome completo/i), 'Ana Souza')
    await user.type(screen.getByLabelText(/^e-mail/i), 'ana@amactive.dev')
    await user.type(screen.getByLabelText(/senha inicial/i), 'senha1234')
    await user.click(screen.getByRole('button', { name: /cadastrar usuário/i }))

    expect(await screen.findByText(/e-mail já cadastrado para outro usuário/i)).toBeInTheDocument()
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(<UsuarioForm onSuccess={vi.fn()} />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
