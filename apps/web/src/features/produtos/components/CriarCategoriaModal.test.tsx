import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe, toHaveNoViolations } from 'jest-axe'
import { ApiError } from '@/shared/lib/api-client'
import { CriarCategoriaModal } from './CriarCategoriaModal'
import type { Categoria, CriarCategoriaDTO } from '../schemas/produto.schema'

expect.extend(toHaveNoViolations)

const categoriasExistentes: Categoria[] = [
  { id: '11111111-1111-1111-1111-111111111111', nome: 'Leggings', slug: 'leggings', ativo: true },
  { id: '22222222-2222-2222-2222-222222222222', nome: 'Tops', slug: 'tops', ativo: true },
]

const categoriaRecemCriada: Categoria = {
  id: '33333333-3333-3333-3333-333333333333',
  nome: 'Conjuntos',
  slug: 'conjuntos',
  ativo: true,
}

type MutateOptions = {
  onSuccess?: (categoria: Categoria) => void
  onError?: (error: unknown) => void
}

let comportamento: 'sucesso' | 'erro-backend' = 'sucesso'
const mutateMock = vi.fn((_payload: CriarCategoriaDTO, options?: MutateOptions) => {
  if (comportamento === 'erro-backend') {
    options?.onError?.(new ApiError('Conflito', 409, 'Categoria já cadastrada com esse nome'))
    return
  }
  options?.onSuccess?.(categoriaRecemCriada)
})

vi.mock('../hooks/useCriarCategoria', () => ({
  useCriarCategoria: () => ({ mutate: mutateMock, isPending: false }),
}))

describe('CriarCategoriaModal', () => {
  afterEach(() => {
    comportamento = 'sucesso'
    vi.clearAllMocks()
  })

  it('não renderiza nada quando fechado', () => {
    render(
      <CriarCategoriaModal
        open={false}
        onClose={vi.fn()}
        categoriasExistentes={categoriasExistentes}
        onCriada={vi.fn()}
      />,
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('exibe o campo de nome quando aberto', () => {
    render(
      <CriarCategoriaModal open onClose={vi.fn()} categoriasExistentes={categoriasExistentes} onCriada={vi.fn()} />,
    )

    expect(screen.getByRole('dialog', { name: 'Nova categoria' })).toBeInTheDocument()
    expect(screen.getByLabelText(/nome da categoria/i)).toBeInTheDocument()
  })

  it('bloqueia submissão com nome vazio (validação Zod)', async () => {
    const user = userEvent.setup()
    render(
      <CriarCategoriaModal open onClose={vi.fn()} categoriasExistentes={categoriasExistentes} onCriada={vi.fn()} />,
    )

    await user.click(screen.getByRole('button', { name: /criar categoria/i }))

    expect(await screen.findByText('Informe o nome da categoria')).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it('bloqueia criação de categoria com nome já existente na lista carregada', async () => {
    const user = userEvent.setup()
    render(
      <CriarCategoriaModal open onClose={vi.fn()} categoriasExistentes={categoriasExistentes} onCriada={vi.fn()} />,
    )

    // Mesmo nome já cadastrado, variando apenas caixa/espaços.
    await user.type(screen.getByLabelText(/nome da categoria/i), '  leggings  ')
    await user.click(screen.getByRole('button', { name: /criar categoria/i }))

    expect(await screen.findByText('Já existe uma categoria com esse nome')).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it('cria a categoria com sucesso, notifica o formulário e fecha o modal', async () => {
    const user = userEvent.setup()
    const onCriada = vi.fn()
    const onClose = vi.fn()
    render(
      <CriarCategoriaModal open onClose={onClose} categoriasExistentes={categoriasExistentes} onCriada={onCriada} />,
    )

    await user.type(screen.getByLabelText(/nome da categoria/i), 'Conjuntos')
    await user.click(screen.getByRole('button', { name: /criar categoria/i }))

    expect(mutateMock).toHaveBeenCalledWith({ nome: 'Conjuntos' }, expect.anything())
    expect(onCriada).toHaveBeenCalledWith(categoriaRecemCriada)
    expect(onClose).toHaveBeenCalled()
  })

  it('exibe o erro do backend quando a duplicidade só é detectada no servidor', async () => {
    comportamento = 'erro-backend'
    const user = userEvent.setup()
    const onCriada = vi.fn()
    render(
      <CriarCategoriaModal open onClose={vi.fn()} categoriasExistentes={categoriasExistentes} onCriada={onCriada} />,
    )

    await user.type(screen.getByLabelText(/nome da categoria/i), 'Categoria Nova')
    await user.click(screen.getByRole('button', { name: /criar categoria/i }))

    expect(await screen.findByText('Categoria já cadastrada com esse nome')).toBeInTheDocument()
    expect(onCriada).not.toHaveBeenCalled()
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(
      <CriarCategoriaModal open onClose={vi.fn()} categoriasExistentes={categoriasExistentes} onCriada={vi.fn()} />,
    )

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
