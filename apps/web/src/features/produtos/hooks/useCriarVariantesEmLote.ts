import { useMutation, useQueryClient } from '@tanstack/react-query'
import { getErrorMessage } from '@/shared/lib/get-error-message'
import { toast } from '@/shared/lib/toast'
import { produtoService } from '../services/produto.service'
import type { ComboVarianteMatriz } from '../lib/matriz-variantes'
import type { Variante } from '../types/produto.types'

export type ResultadoCombo = {
  combo: ComboVarianteMatriz
  variante?: Variante
  erro?: string
}

type Variables = {
  combos: ComboVarianteMatriz[]
  // Chamado após cada combinação ser processada (sucesso ou falha) — usado
  // pela UI para exibir progresso "x de y" em tempo real.
  onProgresso?: (resultado: ResultadoCombo, indiceConcluido: number, total: number) => void
}

// Orquestra a criação da matriz cor × tamanho: o backend não tem um endpoint
// de criação em lote (POST /produtos/{id}/variantes cria uma variante por
// chamada, ver docs/openapi.yaml), então disparamos uma chamada por
// combinação, sequencialmente. Uma falha isolada (ex: SKU duplicado) nunca
// aborta as demais — cada resultado é reportado individualmente.
export function useCriarVariantesEmLote(produtoId: string) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ combos, onProgresso }: Variables): Promise<ResultadoCombo[]> => {
      const resultados: ResultadoCombo[] = []

      for (const combo of combos) {
        let resultado: ResultadoCombo
        try {
          const variante = await produtoService.criarVariante(produtoId, {
            sku: combo.sku,
            tamanho: combo.tamanho,
            cor: combo.cor,
            preco_venda: combo.precoVenda,
            preco_custo: combo.precoCusto || undefined,
            estoque_inicial: combo.estoqueInicial,
          })
          resultado = { combo, variante }
        } catch (err) {
          resultado = { combo, erro: getErrorMessage(err) }
        }
        resultados.push(resultado)
        onProgresso?.(resultado, resultados.length, combos.length)
      }

      return resultados
    },
    onSuccess: (resultados) => {
      queryClient.invalidateQueries({ queryKey: ['produtos', 'detail', produtoId] })
      queryClient.invalidateQueries({ queryKey: ['estoque'] })

      const sucessos = resultados.filter((r) => !r.erro).length
      const falhas = resultados.length - sucessos
      if (falhas === 0) {
        toast.success(`${sucessos} variante(s) criada(s) com sucesso!`)
      } else if (sucessos === 0) {
        toast.error(`Nenhuma variante foi criada. ${falhas} combinação(ões) falharam.`)
      } else {
        toast.error(`${sucessos} variante(s) criada(s), ${falhas} falharam. Veja os detalhes abaixo.`)
      }
    },
  })
}
