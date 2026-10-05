// Carrinho da vitrine. Estado do navegador do cliente (sem login): persiste em
// localStorage só para o carrinho sobreviver a um recarregamento.
//
// A quantidade e o preço guardados aqui são uma *cópia para exibição*. A regra
// de verdade (saldo, desconto, preço) é recalculada pelo backend no checkout.

import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'

// Mesmo teto aceito pela API (CheckoutRequest.itens.quantidade, le=20).
export const LIMITE_QUANTIDADE_POR_ITEM = 20

export type ItemCarrinho = {
  varianteId: string
  produtoId: string
  produtoNome: string
  cor: string
  tamanho: string
  sku: string
  precoUnitario: string
  precoCheio: string
  /** Saldo disponível no momento em que o item foi visto no catálogo. */
  disponivel: number
  quantidade: number
}

type NovoItem = Omit<ItemCarrinho, 'quantidade'>

type CarrinhoState = {
  itens: ItemCarrinho[]
  adicionar: (item: NovoItem, quantidade: number) => void
  alterarQuantidade: (varianteId: string, quantidade: number) => void
  remover: (varianteId: string) => void
  limpar: () => void
}

function tetoDoItem(disponivel: number): number {
  return Math.min(disponivel, LIMITE_QUANTIDADE_POR_ITEM)
}

export const useCarrinhoStore = create<CarrinhoState>()(
  persist(
    (set) => ({
      itens: [],

      adicionar: (novo, quantidade) =>
        set((estado) => {
          const existente = estado.itens.find((i) => i.varianteId === novo.varianteId)
          if (existente) {
            const quantidadeFinal = Math.min(
              existente.quantidade + quantidade,
              tetoDoItem(novo.disponivel),
            )
            return {
              itens: estado.itens.map((i) =>
                i.varianteId === novo.varianteId
                  ? {
                      ...i,
                      disponivel: novo.disponivel,
                      precoUnitario: novo.precoUnitario,
                      precoCheio: novo.precoCheio,
                      quantidade: Math.max(quantidadeFinal, 0),
                    }
                  : i,
              ),
            }
          }
          const quantidadeInicial = Math.min(quantidade, tetoDoItem(novo.disponivel))
          if (quantidadeInicial <= 0) return estado
          return { itens: [...estado.itens, { ...novo, quantidade: quantidadeInicial }] }
        }),

      alterarQuantidade: (varianteId, quantidade) =>
        set((estado) => ({
          itens: estado.itens.map((i) => {
            if (i.varianteId !== varianteId) return i
            const limite = tetoDoItem(i.disponivel)
            return { ...i, quantidade: Math.min(Math.max(quantidade, 1), limite) }
          }),
        })),

      remover: (varianteId) =>
        set((estado) => ({ itens: estado.itens.filter((i) => i.varianteId !== varianteId) })),

      limpar: () => set({ itens: [] }),
    }),
    {
      name: 'amactive.loja.carrinho',
      // createJSONStorage cai para armazenamento inexistente (ex.: navegação
      // privada com site data bloqueado) sem quebrar a vitrine.
      storage: createJSONStorage(() => localStorage),
    },
  ),
)

/** Total em centavos, para somar sem erro de ponto flutuante. */
export function totalEmCentavos(itens: ItemCarrinho[]): number {
  return itens.reduce(
    (soma, item) => soma + Math.round(Number(item.precoUnitario) * 100) * item.quantidade,
    0,
  )
}

export function quantidadeDeItens(itens: ItemCarrinho[]): number {
  return itens.reduce((soma, item) => soma + item.quantidade, 0)
}
