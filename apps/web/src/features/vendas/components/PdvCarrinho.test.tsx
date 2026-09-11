import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe, toHaveNoViolations } from 'jest-axe'
import { PdvCarrinho } from './PdvCarrinho'
import { useCarrinhoStore } from '../store/carrinho.store'
import type { CarrinhoItem } from '../types/pedido.types'

expect.extend(toHaveNoViolations)

vi.mock('@/features/clientes', () => ({
  useClientes: () => ({ data: { data: [], pagination: { total: 0, page: 1, per_page: 10 } } }),
}))

function makeItem(overrides: Partial<CarrinhoItem> = {}): CarrinhoItem {
  return {
    varianteId: 'variante-1',
    sku: 'LEG-CORAL-M',
    produtoNome: 'Legging Fitness',
    tamanho: 'M',
    cor: 'Coral',
    precoUnitario: '100.00',
    quantidade: 1,
    descontoItem: '0.00',
    estoqueDisponivel: 10,
    ...overrides,
  }
}

// Testes do carrinho do PDV (estado Zustand + interação de UI).
describe('PdvCarrinho', () => {
  beforeEach(() => {
    useCarrinhoStore.getState().clear()
  })

  afterEach(() => {
    useCarrinhoStore.getState().clear()
  })

  it('exibe estado vazio quando não há itens no carrinho', () => {
    render(<PdvCarrinho />)
    expect(screen.getByText('Carrinho vazio')).toBeInTheDocument()
  })

  it('lista os itens do carrinho com subtotal calculado', () => {
    useCarrinhoStore.getState().addItem(makeItem({ quantidade: 2, precoUnitario: '100.00' }))

    render(<PdvCarrinho />)

    expect(screen.getByText(/Legging Fitness/)).toBeInTheDocument()
    // Com um único item, o subtotal da linha e o subtotal geral coincidem (R$ 200,00 aparece duas vezes)
    expect(screen.getAllByText('R$ 200,00')).toHaveLength(2)
  })

  it('aumenta a quantidade ao clicar em +, respeitando o estoque disponível', async () => {
    const user = userEvent.setup()
    useCarrinhoStore.getState().addItem(makeItem({ quantidade: 1, estoqueDisponivel: 2 }))

    render(<PdvCarrinho />)

    await user.click(screen.getByRole('button', { name: /aumentar quantidade/i }))
    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(2)

    const increaseButton = screen.getByRole('button', { name: /aumentar quantidade/i })
    expect(increaseButton).toBeDisabled()
  })

  it('remove o item ao clicar no botão de remover', async () => {
    const user = userEvent.setup()
    useCarrinhoStore.getState().addItem(makeItem())

    render(<PdvCarrinho />)
    await user.click(screen.getByRole('button', { name: /remover/i }))

    expect(useCarrinhoStore.getState().itens).toHaveLength(0)
    expect(screen.getByText('Carrinho vazio')).toBeInTheDocument()
  })

  it('não tem violações de acessibilidade com itens no carrinho', async () => {
    useCarrinhoStore.getState().addItem(makeItem())
    const { container } = render(<PdvCarrinho />)

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('exibe o preço riscado, o preço promocional e o badge de promoção quando o item tem desconto', () => {
    useCarrinhoStore.getState().addItem(
      makeItem({
        quantidade: 2,
        precoUnitario: '100.00',
        precoPromocional: '85.00',
        descontoPercentual: '15.00',
        descontoItem: '30.00',
      }),
    )

    render(<PdvCarrinho />)

    expect(screen.getByText('R$ 100,00')).toHaveClass('line-through')
    expect(screen.getByText('R$ 85,00')).toBeInTheDocument()
    expect(screen.getByText('Promoção -15%')).toBeInTheDocument()
  })

  it('o subtotal do item e o total do carrinho refletem o desconto promocional aplicado', () => {
    useCarrinhoStore.getState().addItem(
      makeItem({
        quantidade: 2,
        precoUnitario: '100.00',
        precoPromocional: '85.00',
        descontoPercentual: '15.00',
        descontoItem: '30.00',
      }),
    )

    render(<PdvCarrinho />)

    // Preço unitário 100 x 2 = 200, desconto 30 => subtotal do item = 170,
    // e como é o único item, o subtotal geral do carrinho também é 170.
    expect(screen.getAllByText('R$ 170,00')).toHaveLength(2)
  })
})
