import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe, toHaveNoViolations } from 'jest-axe'
import { ProdutoForm } from './ProdutoForm'
import type { Categoria, CriarCategoriaDTO } from '../schemas/produto.schema'

expect.extend(toHaveNoViolations)

const categoriasIniciais: Categoria[] = [
  { id: '11111111-1111-1111-1111-111111111111', nome: 'Leggings', slug: 'leggings', ativo: true },
]
const categoriaCriada: Categoria = {
  id: '22222222-2222-2222-2222-222222222222',
  nome: 'Tops',
  slug: 'tops',
  ativo: true,
}

vi.mock('../hooks/useCategorias', () => ({
  useCategorias: () => ({ data: { data: categoriasIniciais } }),
}))

type MutateOptions = { onSuccess?: (categoria: Categoria) => void }
const mutateMock = vi.fn((_payload: CriarCategoriaDTO, options?: MutateOptions) => {
  options?.onSuccess?.(categoriaCriada)
})

vi.mock('../hooks/useCriarCategoria', () => ({
  useCriarCategoria: () => ({ mutate: mutateMock, isPending: false }),
}))

describe('ProdutoForm — criação de categoria inline', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('abre o modal de nova categoria ao clicar no botão', async () => {
    const user = userEvent.setup()
    render(<ProdutoForm onSubmit={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: /nova categoria/i }))

    expect(screen.getByRole('dialog', { name: 'Nova categoria' })).toBeInTheDocument()
  })

  it('seleciona automaticamente a categoria recém-criada no select do produto', async () => {
    const user = userEvent.setup()
    render(<ProdutoForm onSubmit={vi.fn()} />)

    await user.click(screen.getByRole('button', { name: /nova categoria/i }))
    await user.type(screen.getByLabelText(/nome da categoria/i), 'Tops')
    await user.click(screen.getByRole('button', { name: /^criar categoria$/i }))

    // Modal fecha após sucesso.
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    const select = screen.getByLabelText('Categoria') as HTMLSelectElement
    expect(select.value).toBe('22222222-2222-2222-2222-222222222222')
    expect(screen.getByRole('option', { name: 'Tops' })).toBeInTheDocument()
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(<ProdutoForm onSubmit={vi.fn()} />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
