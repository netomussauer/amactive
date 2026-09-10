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

  it('exibe mensagem amigável de estoque insuficiente em erro 422', () => {
    mockError = new ApiError('Erro de validação', 422, 'Estoque insuficiente para a variante X')

    render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

    expect(screen.getByText(/estoque insuficiente para um ou mais itens/i)).toBeInTheDocument()
  })
})
