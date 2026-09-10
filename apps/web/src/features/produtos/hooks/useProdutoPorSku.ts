import { useQuery } from '@tanstack/react-query'
import { produtoService } from '../services/produto.service'

// Usado pelo PDV (feature vendas) para resolver um SKU digitado/escaneado em
// uma variante completa (preço, tamanho, cor, saldo). Exposto no barrel
// público da feature — ver docs/frontend-architecture.md §3 (regra de
// fronteira: "vendas pode importar useProdutoPorSku exportado por produtos/index.ts").
export function useProdutoPorSku(sku: string, enabled: boolean) {
  return useQuery({
    queryKey: ['produtos', 'por-sku', sku],
    queryFn: () => produtoService.buscarVariantePorSku(sku),
    enabled: enabled && sku.trim().length > 0,
    staleTime: 15_000,
    retry: false,
  })
}
