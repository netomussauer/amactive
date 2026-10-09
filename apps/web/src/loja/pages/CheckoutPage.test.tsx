import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { queryClient } from '@/shared/lib/query-client'
import { toast } from '@/shared/lib/toast'
import { ApiError } from '@/shared/lib/api-client'
import * as lojaApi from '../api/loja.api'
import { useCarrinhoStore, type ItemCarrinho } from '../store/carrinho.store'
import type { PedidoCheckoutLoja } from '../schemas/loja.schema'
import { CheckoutPage } from './CheckoutPage'

// Mesmo motivo de ProdutoNovoPage.test.tsx: exercita o ciclo REAL do
// TanStack Query (useMutation + QueryClient real da app), não o hook
// mockado — é a única forma de pegar bugs como o do crypto.randomUUID
// (2026-10-08), que só aparecem na interação real entre mutation e toast.
const item: ItemCarrinho = {
  varianteId: 'v-1',
  produtoId: 'p-1',
  produtoNome: 'Legging Fitness Alta Compressão',
  cor: 'Preto',
  tamanho: 'M',
  sku: 'LEG-PRETO-M',
  precoUnitario: '116.91',
  precoCheio: '129.90',
  disponivel: 3,
  quantidade: 2,
}

const pedidoCriado: PedidoCheckoutLoja = {
  numero: 'PED-001494',
  status: 'PENDENTE',
  subtotal: '233.82',
  valor_total: '233.82',
  reservado_ate: '2026-10-10T13:00:52.509990Z',
  itens: [
    { sku: 'LEG-PRETO-M', descricao: 'Legging Fitness Alta Compressão Preto M', quantidade: 2, preco_unitario: '116.91', subtotal: '233.82' },
  ],
}

function renderizar() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/finalizar']}>
        <Routes>
          <Route path="/finalizar" element={<CheckoutPage />} />
          <Route path="/pedido-enviado" element={<p>Tela de pedido enviado</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('CheckoutPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    queryClient.clear()
    useCarrinhoStore.setState({ itens: [] })
    localStorage.clear()
  })

  it('mostra estado vazio sem itens no carrinho', () => {
    useCarrinhoStore.setState({ itens: [] })
    renderizar()

    expect(screen.getByText('Nenhuma peça no carrinho')).toBeInTheDocument()
  })

  it('bloqueia o envio com telefone inválido (validação Zod)', async () => {
    useCarrinhoStore.setState({ itens: [item] })
    const criar = vi.spyOn(lojaApi, 'criarPedidoLoja')
    const user = userEvent.setup()
    renderizar()

    await user.type(screen.getByLabelText(/^Nome/), 'Ana Cliente')
    await user.type(screen.getByLabelText(/^WhatsApp/), '123')
    await user.click(screen.getByRole('button', { name: 'Enviar pedido' }))

    expect(await screen.findByText(/Informe um telefone com DDD/)).toBeInTheDocument()
    expect(criar).not.toHaveBeenCalled()
  })

  it('envia o pedido e navega para a confirmação, limpando o carrinho', async () => {
    useCarrinhoStore.setState({ itens: [item] })
    const criar = vi.spyOn(lojaApi, 'criarPedidoLoja').mockResolvedValue(pedidoCriado)
    const user = userEvent.setup()
    renderizar()

    await user.type(screen.getByLabelText(/^Nome/), 'Ana Cliente')
    await user.type(screen.getByLabelText(/^WhatsApp/), '(11) 99999-0000')
    await user.click(screen.getByRole('button', { name: 'Enviar pedido' }))

    await waitFor(() => expect(screen.getByText('Tela de pedido enviado')).toBeInTheDocument())
    expect(criar).toHaveBeenCalledWith({
      cliente: { nome: 'Ana Cliente', telefone: '(11) 99999-0000' },
      observacao: undefined,
      itens: [{ variante_id: 'v-1', quantidade: 2 }],
    })
    expect(useCarrinhoStore.getState().itens).toEqual([])
  })

  it('mostra erro (toast) quando o estoque não é mais suficiente', async () => {
    useCarrinhoStore.setState({ itens: [item] })
    vi.spyOn(lojaApi, 'criarPedidoLoja').mockRejectedValue(
      new ApiError(
        'Estoque insuficiente',
        422,
        "Produto 'Legging Fitness Alta Compressão' (LEG-PRETO-M): restam 1 unidade(s) disponível(is).",
      ),
    )
    const toastError = vi.spyOn(toast, 'error')
    const user = userEvent.setup()
    renderizar()

    await user.type(screen.getByLabelText(/^Nome/), 'Ana Cliente')
    await user.type(screen.getByLabelText(/^WhatsApp/), '(11) 99999-0000')
    await user.click(screen.getByRole('button', { name: 'Enviar pedido' }))

    await waitFor(() => expect(toastError).toHaveBeenCalled())
    // Carrinho continua intacto: o pedido não foi concluído.
    expect(useCarrinhoStore.getState().itens).toEqual([item])
  })
})
