import { beforeEach, describe, expect, it } from 'vitest'
import { useCarrinhoStore } from './carrinho.store'
import type { CarrinhoItem } from '../types/pedido.types'

function makeItem(overrides: Partial<CarrinhoItem> = {}): CarrinhoItem {
  return {
    varianteId: 'variante-1',
    sku: 'LEG-CORAL-M',
    produtoNome: 'Legging Fitness',
    tamanho: 'M',
    cor: 'Coral',
    precoUnitario: '129.90',
    quantidade: 1,
    descontoItem: '0.00',
    estoqueDisponivel: 10,
    ...overrides,
  }
}

// Testes do estado local do carrinho (Zustand) do PDV.
describe('carrinho.store', () => {
  beforeEach(() => {
    useCarrinhoStore.getState().clear()
  })

  it('adiciona um novo item ao carrinho', () => {
    useCarrinhoStore.getState().addItem(makeItem())

    expect(useCarrinhoStore.getState().itens).toHaveLength(1)
    expect(useCarrinhoStore.getState().itens[0].sku).toBe('LEG-CORAL-M')
  })

  it('soma a quantidade ao adicionar a mesma variante duas vezes', () => {
    useCarrinhoStore.getState().addItem(makeItem({ quantidade: 2 }))
    useCarrinhoStore.getState().addItem(makeItem({ quantidade: 3 }))

    const itens = useCarrinhoStore.getState().itens
    expect(itens).toHaveLength(1)
    expect(itens[0].quantidade).toBe(5)
  })

  it('não permite ultrapassar o estoque disponível ao somar quantidades', () => {
    useCarrinhoStore.getState().addItem(makeItem({ quantidade: 8, estoqueDisponivel: 10 }))
    useCarrinhoStore.getState().addItem(makeItem({ quantidade: 5, estoqueDisponivel: 10 }))

    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(10)
  })

  it('remove um item do carrinho', () => {
    useCarrinhoStore.getState().addItem(makeItem())
    useCarrinhoStore.getState().removeItem('variante-1')

    expect(useCarrinhoStore.getState().itens).toHaveLength(0)
  })

  it('atualiza a quantidade respeitando o mínimo de 1 e o estoque disponível', () => {
    useCarrinhoStore.getState().addItem(makeItem({ quantidade: 1, estoqueDisponivel: 3 }))

    useCarrinhoStore.getState().updateQuantidade('variante-1', 0)
    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(1)

    useCarrinhoStore.getState().updateQuantidade('variante-1', 10)
    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(3)
  })

  it('calcula o desconto proporcionalmente ao somar quantidade de um item com preço promocional', () => {
    useCarrinhoStore.getState().addItem(
      makeItem({
        quantidade: 1,
        precoUnitario: '100.00',
        precoPromocional: '85.00',
        descontoPercentual: '15.00',
        descontoItem: '15.00',
        estoqueDisponivel: 10,
      }),
    )
    useCarrinhoStore.getState().addItem(
      makeItem({
        quantidade: 2,
        precoUnitario: '100.00',
        precoPromocional: '85.00',
        descontoPercentual: '15.00',
        descontoItem: '30.00',
        estoqueDisponivel: 10,
      }),
    )

    const item = useCarrinhoStore.getState().itens[0]
    expect(item.quantidade).toBe(3)
    expect(item.descontoItem).toBe('45.00')
  })

  it('recalcula o desconto ao aumentar a quantidade de um item com preço promocional', () => {
    useCarrinhoStore.getState().addItem(
      makeItem({
        quantidade: 1,
        precoUnitario: '100.00',
        precoPromocional: '85.00',
        descontoPercentual: '15.00',
        descontoItem: '15.00',
        estoqueDisponivel: 10,
      }),
    )

    useCarrinhoStore.getState().updateQuantidade('variante-1', 4)

    const item = useCarrinhoStore.getState().itens[0]
    expect(item.quantidade).toBe(4)
    expect(item.descontoItem).toBe('60.00')
  })

  it('recalcula o desconto ao diminuir a quantidade de um item com preço promocional', () => {
    useCarrinhoStore.getState().addItem(
      makeItem({
        quantidade: 4,
        precoUnitario: '100.00',
        precoPromocional: '85.00',
        descontoPercentual: '15.00',
        descontoItem: '60.00',
        estoqueDisponivel: 10,
      }),
    )

    useCarrinhoStore.getState().updateQuantidade('variante-1', 2)

    const item = useCarrinhoStore.getState().itens[0]
    expect(item.quantidade).toBe(2)
    expect(item.descontoItem).toBe('30.00')
  })

  it('mantém desconto "0.00" ao atualizar quantidade de item sem promoção', () => {
    useCarrinhoStore.getState().addItem(makeItem({ quantidade: 1, estoqueDisponivel: 10 }))

    useCarrinhoStore.getState().updateQuantidade('variante-1', 5)

    expect(useCarrinhoStore.getState().itens[0].descontoItem).toBe('0.00')
  })

  it('limpa o carrinho, cliente e observação', () => {
    useCarrinhoStore.getState().addItem(makeItem())
    useCarrinhoStore.getState().setClienteId('cliente-1')
    useCarrinhoStore.getState().setObservacao('Entrega rápida')

    useCarrinhoStore.getState().clear()

    expect(useCarrinhoStore.getState().itens).toHaveLength(0)
    expect(useCarrinhoStore.getState().clienteId).toBeNull()
    expect(useCarrinhoStore.getState().observacao).toBe('')
  })

  it('começa no canal PDV, troca de canal sem tocar nos itens e volta a PDV no clear()', () => {
    expect(useCarrinhoStore.getState().origemCanal).toBe('PDV')

    useCarrinhoStore.getState().addItem(makeItem())
    useCarrinhoStore.getState().setOrigemCanal('NUVEMSHOP')

    expect(useCarrinhoStore.getState().origemCanal).toBe('NUVEMSHOP')
    expect(useCarrinhoStore.getState().itens).toHaveLength(1)

    useCarrinhoStore.getState().clear()

    expect(useCarrinhoStore.getState().origemCanal).toBe('PDV')
  })
})
