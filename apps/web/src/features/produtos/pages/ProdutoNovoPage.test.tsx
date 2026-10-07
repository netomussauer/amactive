import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { queryClient } from '@/shared/lib/query-client'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'
import type { Produto } from '../types/produto.types'
import { ProdutoNovoPage } from './ProdutoNovoPage'

// Diferente dos outros testes de features/produtos, aqui NÃO mockamos
// useCriarProduto nem useCategorias — o relato era justamente de um produto
// criado no backend sem nenhum retorno visível no frontend (nem navegação
// pro passo 2, nem toast), então o bug só aparece exercitando o ciclo real
// do TanStack Query (useMutation + QueryClient de verdade), não o hook
// mockado. Usamos o `queryClient` real da app (shared/lib/query-client.ts)
// porque é lá que mora o onError global que pode mascarar o problema.
function renderizar() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/produtos/novo']}>
        <ProdutoNovoPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

const produtoCriado: Produto = {
  id: 'produto-1',
  nome: 'Legging Fitness Alta Compressão',
  descricao: null,
  categoria_id: null,
  marca: 'AMACTIVE',
  desconto_percentual: null,
  ativo: true,
  criado_em: '2026-10-07T12:00:00Z',
}

describe('ProdutoNovoPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    queryClient.clear()
  })

  it('avança para o passo de variantes e notifica sucesso ao cadastrar o produto', async () => {
    vi.spyOn(produtoService, 'listCategorias').mockResolvedValue({ data: [] })
    vi.spyOn(produtoService, 'create').mockResolvedValue(produtoCriado)
    const toastSuccess = vi.spyOn(toast, 'success')
    const toastError = vi.spyOn(toast, 'error')
    const user = userEvent.setup()

    renderizar()

    await user.type(screen.getByLabelText(/nome do produto/i), produtoCriado.nome)
    await user.click(screen.getByRole('button', { name: 'Cadastrar produto' }))

    // O passo 1 deve dar lugar ao passo 2 (matriz de variantes) e o toast de
    // sucesso deve aparecer — é exatamente isso que o usuário relatou como
    // ausente.
    await waitFor(() => expect(screen.getByText('Matriz de variantes (cor × tamanho)')).toBeInTheDocument())
    expect(screen.queryByRole('button', { name: 'Cadastrar produto' })).not.toBeInTheDocument()
    expect(toastSuccess).toHaveBeenCalledWith('Produto cadastrado com sucesso!')
    expect(toastError).not.toHaveBeenCalled()
    expect(produtoService.create).toHaveBeenCalledTimes(1)
  })

  it('não cria um segundo produto se o usuário clicar em Cadastrar produto várias vezes seguidas', async () => {
    vi.spyOn(produtoService, 'listCategorias').mockResolvedValue({ data: [] })
    const criar = vi.spyOn(produtoService, 'create').mockResolvedValue(produtoCriado)
    const user = userEvent.setup()

    renderizar()

    await user.type(screen.getByLabelText(/nome do produto/i), produtoCriado.nome)
    const botao = screen.getByRole('button', { name: 'Cadastrar produto' })
    await user.click(botao)
    await user.click(botao)
    await user.click(botao)

    await waitFor(() => expect(criar).toHaveBeenCalledTimes(1))
  })
})
