import { beforeEach, describe, expect, it } from 'vitest'
import {
  LIMITE_QUANTIDADE_POR_ITEM,
  quantidadeDeItens,
  totalEmCentavos,
  useCarrinhoStore,
  type ItemCarrinho,
} from './carrinho.store'

const base = {
  varianteId: 'v-1',
  produtoId: 'p-1',
  produtoNome: 'Legging Fitness',
  cor: 'Preto',
  tamanho: 'M',
  sku: 'SKU-1',
  precoUnitario: '89.90',
  precoCheio: '99.90',
  disponivel: 10,
}

describe('carrinho da vitrine', () => {
  beforeEach(() => {
    localStorage.clear()
    useCarrinhoStore.setState({ itens: [] })
  })

  it('adiciona um item novo com a quantidade pedida', () => {
    useCarrinhoStore.getState().adicionar(base, 2)

    expect(useCarrinhoStore.getState().itens).toEqual([{ ...base, quantidade: 2 }])
  })

  it('nunca adiciona acima do saldo disponível visto no catálogo', () => {
    useCarrinhoStore.getState().adicionar({ ...base, disponivel: 3 }, 9)

    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(3)
  })

  it('nunca adiciona acima do teto por item aceito pela API', () => {
    useCarrinhoStore.getState().adicionar({ ...base, disponivel: 500 }, 99)

    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(LIMITE_QUANTIDADE_POR_ITEM)
  })

  it('não adiciona item esgotado', () => {
    useCarrinhoStore.getState().adicionar({ ...base, disponivel: 0 }, 1)

    expect(useCarrinhoStore.getState().itens).toEqual([])
  })

  it('soma à linha existente sem passar do saldo atual, e atualiza o preço visto', () => {
    const { adicionar } = useCarrinhoStore.getState()
    adicionar(base, 4)
    adicionar({ ...base, disponivel: 5, precoUnitario: '79.90' }, 4)

    const [item] = useCarrinhoStore.getState().itens
    expect(item.quantidade).toBe(5)
    expect(item.precoUnitario).toBe('79.90')
  })

  it('alterarQuantidade respeita o mínimo de 1 e o saldo disponível', () => {
    const { adicionar, alterarQuantidade } = useCarrinhoStore.getState()
    adicionar(base, 2)

    alterarQuantidade('v-1', 0)
    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(1)

    alterarQuantidade('v-1', 50)
    expect(useCarrinhoStore.getState().itens[0].quantidade).toBe(10)
  })

  it('remover e limpar esvaziam o carrinho', () => {
    const { adicionar, remover, limpar } = useCarrinhoStore.getState()
    adicionar(base, 1)
    adicionar({ ...base, varianteId: 'v-2', sku: 'SKU-2' }, 1)

    remover('v-1')
    expect(useCarrinhoStore.getState().itens.map((i) => i.varianteId)).toEqual(['v-2'])

    limpar()
    expect(useCarrinhoStore.getState().itens).toEqual([])
  })

  it('persiste o carrinho no navegador para sobreviver a um recarregamento', () => {
    useCarrinhoStore.getState().adicionar(base, 1)

    const salvo = localStorage.getItem('amactive.loja.carrinho')
    expect(salvo).not.toBeNull()
    expect(salvo).toContain('SKU-1')
  })
})

describe('totais do carrinho', () => {
  it('soma em centavos, sem erro de ponto flutuante', () => {
    const itens: ItemCarrinho[] = [
      { ...base, quantidade: 3, precoUnitario: '0.10' },
      { ...base, varianteId: 'v-2', quantidade: 1, precoUnitario: '0.20' },
    ]

    expect(totalEmCentavos(itens)).toBe(50)
    expect(quantidadeDeItens(itens)).toBe(4)
  })
})
