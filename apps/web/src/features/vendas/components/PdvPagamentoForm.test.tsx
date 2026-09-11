import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PdvPagamentoForm } from './PdvPagamentoForm'
import { useCarrinhoStore } from '../store/carrinho.store'
import { ApiError } from '@/shared/lib/api-client'

const mutateMock = vi.fn((_dto: unknown, options?: { onSuccess?: (pedido: unknown) => void }) => {
  options?.onSuccess?.({ id: 'pedido-1', numero: '000001', valor_total: '100.00' })
})

let mockError: unknown = null

vi.mock('../hooks/useCriarPedido', () => ({
  useCriarPedido: () => ({ mutate: mutateMock, isPending: false, error: mockError }),
}))

// Testes do fluxo crítico de pagamento do PDV (soma de pagamentos, 422 de estoque).
describe('PdvPagamentoForm', () => {
  beforeEach(() => {
    mockError = null
    mutateMock.mockClear()
    useCarrinhoStore.getState().clear()
    useCarrinhoStore.getState().addItem({
      varianteId: 'variante-1',
      sku: 'LEG-CORAL-M',
      produtoNome: 'Legging Fitness',
      tamanho: 'M',
      cor: 'Coral',
      precoUnitario: '100.00',
      quantidade: 1,
      descontoItem: '0.00',
      estoqueDisponivel: 10,
    })
  })

  afterEach(() => {
    useCarrinhoStore.getState().clear()
  })

  it('confirma a venda quando a soma dos pagamentos bate com o total', async () => {
    const user = userEvent.setup()
    const onConfirmado = vi.fn()

    render(<PdvPagamentoForm subtotal={100} onConfirmado={onConfirmado} />)

    await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

    expect(mutateMock).toHaveBeenCalledTimes(1)
    const [dto] = mutateMock.mock.calls[0]
    expect(dto).toMatchObject({
      itens: [{ variante_id: 'variante-1', quantidade: 1, desconto_item: '0.00' }],
    })
    expect(onConfirmado).toHaveBeenCalledWith({ id: 'pedido-1', numero: '000001', valor_total: '100.00' })
  })

  it('exibe erro inline quando a soma dos pagamentos diverge do total e não confirma a venda', async () => {
    const user = userEvent.setup()
    const onConfirmado = vi.fn()

    render(<PdvPagamentoForm subtotal={100} onConfirmado={onConfirmado} />)

    const valorInput = screen.getByLabelText(/valor da forma de pagamento 1/i)
    await user.clear(valorInput)
    await user.type(valorInput, '50.00')

    await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

    expect(await screen.findByText(/precisa ser igual ao total a pagar/i)).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it('envia o desconto_item calculado do item promocional e mantém o total exibido consistente com o payload', async () => {
    const user = userEvent.setup()
    const onConfirmado = vi.fn()

    // Item com preço promocional já refletido no desconto_item (ver
    // PdvBuscaProduto/carrinho.store) — subtotal com desconto: 200 - 30 = 170.
    useCarrinhoStore.getState().clear()
    useCarrinhoStore.getState().addItem({
      varianteId: 'variante-promo',
      sku: 'LEG-CORAL-P',
      produtoNome: 'Legging Fitness',
      tamanho: 'P',
      cor: 'Coral',
      precoUnitario: '100.00',
      quantidade: 2,
      descontoItem: '30.00',
      estoqueDisponivel: 10,
      precoPromocional: '85.00',
      descontoPercentual: '15.00',
    })

    render(<PdvPagamentoForm subtotal={170} onConfirmado={onConfirmado} />)

    // O valor padrão da forma de pagamento já nasce igual ao subtotal com desconto.
    expect(screen.getByLabelText(/valor da forma de pagamento 1/i)).toHaveValue('170.00')
    // Subtotal, "Total a pagar" e "Total informado nos pagamentos" todos batem em R$ 170,00.
    expect(screen.getAllByText('R$ 170,00')).toHaveLength(3)

    await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

    expect(mutateMock).toHaveBeenCalledTimes(1)
    const [dto] = mutateMock.mock.calls[0]
    expect(dto).toMatchObject({
      itens: [{ variante_id: 'variante-promo', quantidade: 2, desconto_item: '30.00' }],
      pagamentos: [{ forma_pagamento: 'DINHEIRO', valor: '170.00' }],
    })
  })

  it('exibe mensagem amigável de estoque insuficiente em erro 422', () => {
    mockError = new ApiError('Erro de validação', 422, 'Estoque insuficiente para a variante X')

    render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

    expect(screen.getByText(/estoque insuficiente para um ou mais itens/i)).toBeInTheDocument()
  })
})
