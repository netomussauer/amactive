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

  it('avança no primeiro clique mesmo selecionando uma categoria existente', async () => {
    // Reprodução do relato pós-fix: nome + categoria selecionada no <select>,
    // desconto_percentual intocado — mesmo assim o primeiro clique não
    // navegava nem mostrava toast (produto era criado de verdade no backend).
    vi.spyOn(produtoService, 'listCategorias').mockResolvedValue({
      data: [{ id: '11111111-1111-1111-1111-111111111111', nome: 'Conjuntos', slug: 'conjuntos', ativo: true }],
    })
    vi.spyOn(produtoService, 'create').mockResolvedValue({
      ...produtoCriado,
      categoria_id: '11111111-1111-1111-1111-111111111111',
    })
    const toastSuccess = vi.spyOn(toast, 'success')
    const user = userEvent.setup()

    renderizar()

    await user.type(screen.getByLabelText(/nome do produto/i), produtoCriado.nome)
    await waitFor(() => expect(screen.getByRole('option', { name: 'Conjuntos' })).toBeInTheDocument())
    await user.selectOptions(screen.getByLabelText(/categoria/i), 'Conjuntos')
    await user.click(screen.getByRole('button', { name: 'Cadastrar produto' }))

    await waitFor(() => expect(screen.getByText('Matriz de variantes (cor × tamanho)')).toBeInTheDocument())
    expect(toastSuccess).toHaveBeenCalledWith('Produto cadastrado com sucesso!')
    expect(produtoService.create).toHaveBeenCalledTimes(1)
  })

  it('avança e notifica mesmo sem crypto.randomUUID (acesso via HTTP puro, fora de contexto seguro)', async () => {
    // Reprodução fiel do bug real (visto no console do navegador em
    // produção/dev, acessado via IP/hostname HTTP puro do laboratório):
    // `crypto.randomUUID` só existe em contexto seguro (HTTPS ou
    // localhost — MDN). Sem ele, toast.push() lançava TypeError dentro do
    // onSuccess global do MutationCache (query-client.ts), o que fazia o
    // TanStack Query tratar a mutation inteira como erro — abortando a
    // navegação pro passo 2 mesmo com o produto já criado no backend. O
    // ambiente de teste (jsdom/Node) tem crypto.randomUUID disponível por
    // padrão, então sem este teste simulando sua ausência o bug não
    // aparece na suíte (foi por isso que passou despercebido no primeiro
    // fix, que mirava só o desconto_percentual).
    // `delete crypto.randomUUID` não funciona (o método vive no protótipo,
    // não é propriedade própria — ver mesma nota em toast-store.test.ts):
    // precisa sombrear com uma propriedade própria `undefined`.
    Object.defineProperty(crypto, 'randomUUID', { value: undefined, configurable: true })
    try {
      vi.spyOn(produtoService, 'listCategorias').mockResolvedValue({ data: [] })
      vi.spyOn(produtoService, 'create').mockResolvedValue(produtoCriado)
      const toastSuccess = vi.spyOn(toast, 'success')
      const user = userEvent.setup()

      renderizar()

      await user.type(screen.getByLabelText(/nome do produto/i), produtoCriado.nome)
      await user.click(screen.getByRole('button', { name: 'Cadastrar produto' }))

      await waitFor(() => expect(screen.getByText('Matriz de variantes (cor × tamanho)')).toBeInTheDocument())
      expect(toastSuccess).toHaveBeenCalledWith('Produto cadastrado com sucesso!')
    } finally {
      // @ts-expect-error -- remove a propriedade própria, voltando a expor o método do protótipo.
      delete crypto.randomUUID
    }
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
