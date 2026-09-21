import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe } from 'jest-axe'
import { PdvCanalSelector } from './PdvCanalSelector'
import { useCarrinhoStore } from '../store/carrinho.store'

// Seletor de canal (segmented control) do topo do PDV.
describe('PdvCanalSelector', () => {
  beforeEach(() => {
    useCarrinhoStore.getState().clear()
  })

  afterEach(() => {
    useCarrinhoStore.getState().clear()
  })

  it('exibe os três canais com PDV selecionado por padrão', () => {
    render(<PdvCanalSelector />)

    expect(screen.getByRole('group', { name: /canal da venda/i })).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'PDV' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'WhatsApp' })).not.toBeChecked()
    expect(screen.getByRole('radio', { name: 'Nuvemshop' })).not.toBeChecked()
  })

  it('atualiza o canal no store ao selecionar outro canal', async () => {
    const user = userEvent.setup()
    render(<PdvCanalSelector />)

    await user.click(screen.getByRole('radio', { name: 'Nuvemshop' }))

    expect(useCarrinhoStore.getState().origemCanal).toBe('NUVEMSHOP')
    expect(screen.getByRole('radio', { name: 'Nuvemshop' })).toBeChecked()
    expect(screen.getByRole('radio', { name: 'PDV' })).not.toBeChecked()
  })

  it('troca de canal não altera itens nem cliente do carrinho', async () => {
    const user = userEvent.setup()
    useCarrinhoStore.getState().addItem({
      varianteId: 'variante-1',
      sku: 'LEG-CORAL-M',
      produtoNome: 'Legging Fitness',
      tamanho: 'M',
      cor: 'Coral',
      precoUnitario: '100.00',
      quantidade: 2,
      descontoItem: '0.00',
      estoqueDisponivel: 10,
    })
    useCarrinhoStore.getState().setClienteId('cliente-1')
    render(<PdvCanalSelector />)

    await user.click(screen.getByRole('radio', { name: 'WhatsApp' }))

    expect(useCarrinhoStore.getState().itens).toHaveLength(1)
    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(2)
    expect(useCarrinhoStore.getState().clienteId).toBe('cliente-1')
  })

  it('é navegável por teclado (setas alternam o canal)', async () => {
    const user = userEvent.setup()
    render(<PdvCanalSelector />)

    screen.getByRole('radio', { name: 'PDV' }).focus()
    await user.keyboard('{ArrowRight}')

    expect(useCarrinhoStore.getState().origemCanal).toBe('WHATSAPP')
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(<PdvCanalSelector />)
    const results = await axe(container)
    expect(results.violations).toEqual([])
  })
})
