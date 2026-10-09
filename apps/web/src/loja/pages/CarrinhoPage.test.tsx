import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { useCarrinhoStore, type ItemCarrinho } from '../store/carrinho.store'
import { CarrinhoPage } from './CarrinhoPage'

// A lógica de soma/teto já é coberta a fundo em carrinho.store.test.ts — aqui
// valida-se só a TELA: o que o cliente vê e consegue fazer com o carrinho
// (que é exatamente o "funcionamento do carrinho" pedido para validar).
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

function renderizar(rota = '/carrinho') {
  return render(
    <MemoryRouter initialEntries={[rota]}>
      <Routes>
        <Route path="/carrinho" element={<CarrinhoPage />} />
        <Route path="/finalizar" element={<p>Tela de checkout</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('CarrinhoPage', () => {
  beforeEach(() => {
    useCarrinhoStore.setState({ itens: [item] })
  })

  afterEach(() => {
    useCarrinhoStore.setState({ itens: [] })
    localStorage.clear()
  })

  it('mostra estado vazio quando não há itens', () => {
    useCarrinhoStore.setState({ itens: [] })
    renderizar()

    expect(screen.getByText('Seu carrinho está vazio')).toBeInTheDocument()
  })

  it('lista o item com subtotal e total corretos', () => {
    renderizar()

    expect(screen.getByText('Legging Fitness Alta Compressão')).toBeInTheDocument()
    expect(screen.getByText(/Preto · M/)).toBeInTheDocument()
    // Subtotal da linha (116.91 × 2) e total do carrinho coincidem (um único
    // item) — aparece duas vezes: na linha do item e no resumo.
    expect(screen.getAllByText('R$ 233,82')).toHaveLength(2)
  })

  it('aumentar/diminuir quantidade atualiza a tela e respeita o saldo visto no catálogo', async () => {
    const user = userEvent.setup()
    renderizar()

    await user.click(screen.getByRole('button', { name: /Aumentar quantidade/ }))
    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(3)
    expect(screen.getByRole('button', { name: /Aumentar quantidade/ })).toBeDisabled()
    expect(screen.getByText('Quantidade máxima disponível')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /Diminuir quantidade/ }))
    await user.click(screen.getByRole('button', { name: /Diminuir quantidade/ }))
    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(1)
    expect(screen.getByRole('button', { name: /Diminuir quantidade/ })).toBeDisabled()
  })

  it('remover o item esvazia o carrinho e mostra o estado vazio', async () => {
    const user = userEvent.setup()
    renderizar()

    await user.click(screen.getByRole('button', { name: /Remover Legging Fitness/ }))

    expect(useCarrinhoStore.getState().itens).toEqual([])
    expect(screen.getByText('Seu carrinho está vazio')).toBeInTheDocument()
  })

  it('"Finalizar pedido" navega para o checkout', async () => {
    const user = userEvent.setup()
    renderizar()

    await user.click(screen.getByRole('button', { name: 'Finalizar pedido' }))

    expect(screen.getByText('Tela de checkout')).toBeInTheDocument()
  })
})
