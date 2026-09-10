import { create } from 'zustand'
import type { CarrinhoItem } from '../types/pedido.types'

type CarrinhoState = {
  itens: CarrinhoItem[]
  clienteId: string | null
  observacao: string
  addItem: (item: CarrinhoItem) => void
  removeItem: (varianteId: string) => void
  updateQuantidade: (varianteId: string, quantidade: number) => void
  setClienteId: (clienteId: string | null) => void
  setObservacao: (observacao: string) => void
  clear: () => void
}

// Estado de rascunho do carrinho do PDV — não existe no servidor até o
// POST /pedidos ser confirmado. Ver docs/frontend-architecture.md §5.4
// (Zustand reservado apenas para este caso).
export const useCarrinhoStore = create<CarrinhoState>((set, get) => ({
  itens: [],
  clienteId: null,
  observacao: '',

  addItem: (item) => {
    const existente = get().itens.find((i) => i.varianteId === item.varianteId)
    if (existente) {
      const novaQuantidade = Math.min(existente.quantidade + item.quantidade, item.estoqueDisponivel)
      set({
        itens: get().itens.map((i) =>
          i.varianteId === item.varianteId ? { ...i, quantidade: novaQuantidade } : i,
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
      itens: get().itens.map((i) =>
        i.varianteId === varianteId
          ? { ...i, quantidade: Math.max(1, Math.min(quantidade, i.estoqueDisponivel)) }
          : i,
      ),
    })
  },

  setClienteId: (clienteId) => set({ clienteId }),
  setObservacao: (observacao) => set({ observacao }),

  clear: () => set({ itens: [], clienteId: null, observacao: '' }),
}))
