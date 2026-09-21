import { create } from 'zustand'
import type { CarrinhoItem, OrigemCanal } from '../types/pedido.types'
import { calcularDescontoItem } from '../lib/calcular-desconto-item'

type CarrinhoState = {
  itens: CarrinhoItem[]
  clienteId: string | null
  observacao: string
  origemCanal: OrigemCanal
  addItem: (item: CarrinhoItem) => void
  removeItem: (varianteId: string) => void
  updateQuantidade: (varianteId: string, quantidade: number) => void
  setClienteId: (clienteId: string | null) => void
  setObservacao: (observacao: string) => void
  setOrigemCanal: (origemCanal: OrigemCanal) => void
  clear: () => void
}

// Estado de rascunho do carrinho do PDV — não existe no servidor até o
// POST /pedidos ser confirmado. Ver docs/frontend-architecture.md §5.4
// (Zustand reservado apenas para este caso).
export const useCarrinhoStore = create<CarrinhoState>((set, get) => ({
  itens: [],
  clienteId: null,
  observacao: '',
  origemCanal: 'PDV',

  addItem: (item) => {
    const existente = get().itens.find((i) => i.varianteId === item.varianteId)
    if (existente) {
      const novaQuantidade = Math.min(existente.quantidade + item.quantidade, item.estoqueDisponivel)
      set({
        itens: get().itens.map((i) =>
          i.varianteId === item.varianteId
            ? {
                ...i,
                quantidade: novaQuantidade,
                // Recalcula o desconto proporcionalmente à nova quantidade —
                // nunca fica travado no valor calculado na primeira adição.
                descontoItem: calcularDescontoItem(i.precoUnitario, i.precoPromocional, novaQuantidade),
              }
            : i,
        ),
      })
      return
    }
    set({ itens: [...get().itens, item] })
  },

  removeItem: (varianteId) => {
    set({ itens: get().itens.filter((i) => i.varianteId !== varianteId) })
  },

  updateQuantidade: (varianteId, quantidade) => {
    set({
      itens: get().itens.map((i) => {
        if (i.varianteId !== varianteId) return i
        const novaQuantidade = Math.max(1, Math.min(quantidade, i.estoqueDisponivel))
        return {
          ...i,
          quantidade: novaQuantidade,
          descontoItem: calcularDescontoItem(i.precoUnitario, i.precoPromocional, novaQuantidade),
        }
      }),
    })
  },

  setClienteId: (clienteId) => set({ clienteId }),
  setObservacao: (observacao) => set({ observacao }),
  setOrigemCanal: (origemCanal) => set({ origemCanal }),

  clear: () => set({ itens: [], clienteId: null, observacao: '', origemCanal: 'PDV' }),
}))
