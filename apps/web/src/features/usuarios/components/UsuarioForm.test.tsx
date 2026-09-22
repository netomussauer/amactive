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
let proximoErro: unknown = null
const mutateMock = vi.fn((_payload: CriarUsuarioDTO, options?: MutateOptions) => {
  if (proximoErro) {
    options?.onError?.(proximoErro)
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
    proximoErro = null
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
    proximoErro = new ApiError('Conflito', 409, 'E-mail já cadastrado para outro usuário.')
    const user = userEvent.setup()
    render(<UsuarioForm onSuccess={vi.fn()} />)

    await user.type(screen.getByLabelText(/nome completo/i), 'Ana Souza')
    await user.type(screen.getByLabelText(/^e-mail/i), 'ana@amactive.dev')
    await user.type(screen.getByLabelText(/senha inicial/i), 'senha1234')
    await user.click(screen.getByRole('button', { name: /cadastrar usuário/i }))

    expect(await screen.findByText(/e-mail já cadastrado para outro usuário/i)).toBeInTheDocument()
  })

  it('não culpa o e-mail em erro de rede — não é garantido que o cadastro falhou', async () => {
    // "Failed to fetch" pode significar que a resposta se perdeu DEPOIS de
    // a API já ter criado o usuário (ver UsuarioForm.tsx) — marcar o campo
    // de e-mail aqui mentiria dizendo "verifique o e-mail" sobre um
    // cadastro que pode já ter acontecido. O toast genérico (fora do
    // escopo deste componente) é quem mostra a mensagem real.
    proximoErro = new TypeError('Failed to fetch')
    const user = userEvent.setup()
    const onSuccess = vi.fn()
    render(<UsuarioForm onSuccess={onSuccess} />)

    await user.type(screen.getByLabelText(/nome completo/i), 'Ana Souza')
    await user.type(screen.getByLabelText(/^e-mail/i), 'ana@amactive.dev')
    await user.type(screen.getByLabelText(/senha inicial/i), 'senha1234')
    await user.click(screen.getByRole('button', { name: /cadastrar usuário/i }))

    expect(mutateMock).toHaveBeenCalled()
    expect(onSuccess).not.toHaveBeenCalled()
    expect(screen.queryByText(/verifique o e-mail/i)).not.toBeInTheDocument()
    expect(screen.queryByLabelText(/^e-mail/i)).not.toHaveAttribute('aria-invalid', 'true')
  })

  it('não culpa o e-mail em erro 500 do servidor', async () => {
    proximoErro = new ApiError('Erro interno', 500, undefined)
    const user = userEvent.setup()
    render(<UsuarioForm onSuccess={vi.fn()} />)

    await user.type(screen.getByLabelText(/nome completo/i), 'Ana Souza')
    await user.type(screen.getByLabelText(/^e-mail/i), 'ana@amactive.dev')
    await user.type(screen.getByLabelText(/senha inicial/i), 'senha1234')
    await user.click(screen.getByRole('button', { name: /cadastrar usuário/i }))

    expect(mutateMock).toHaveBeenCalled()
    expect(screen.queryByLabelText(/^e-mail/i)).not.toHaveAttribute('aria-invalid', 'true')
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(<UsuarioForm onSuccess={vi.fn()} />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
