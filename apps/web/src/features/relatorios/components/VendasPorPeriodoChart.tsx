import { Spinner } from '@/shared/components/ui/Spinner'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { formatCurrencyBRL, formatDate } from '@/shared/lib/format'
import type { VendaPorDia } from '../types/relatorio.types'

type Props = {
  vendas: VendaPorDia[]
  isLoading: boolean
}

// Gráfico de barras leve, sem dependência externa (evita adicionar uma
// biblioteca de charts pesada só para este painel interno — ver
// docs/frontend-architecture.md §6 "componentes pesados sob demanda").
export function VendasPorPeriodoChart({ vendas, isLoading }: Props) {
  if (isLoading) return <Spinner label="Carregando vendas do período..." />

  if (vendas.length === 0) {
    return <EmptyState title="Sem vendas no período selecionado" description="Ajuste o período para ver o gráfico de faturamento." />
  }

  const maiorFaturamento = Math.max(...vendas.map((v) => Number(v.faturamento)), 1)

  return (
    <div>
      <div className="flex h-48 items-end gap-1.5" role="img" aria-label="Gráfico de faturamento por dia">
        {vendas.map((venda) => {
          const alturaPercentual = Math.max(4, (Number(venda.faturamento) / maiorFaturamento) * 100)
          return (
            <div key={venda.dia} className="group relative flex-1">
              <div
                className="w-full rounded-t bg-primary transition-colors group-hover:bg-primary-hover"
                style={{ height: `${alturaPercentual}%` }}
              />
              <div className="pointer-events-none absolute bottom-full left-1/2 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-md bg-graphite-900 px-2 py-1 text-xs text-white group-hover:block">
                {formatDate(venda.dia)} · {formatCurrencyBRL(venda.faturamento)}
              </div>
            </div>
          )
        })}
      </div>
      <div className="mt-2 flex justify-between text-xs text-text-muted">
        <span>{formatDate(vendas[0]?.dia)}</span>
        <span>{formatDate(vendas[vendas.length - 1]?.dia)}</span>
      </div>
    </div>
  )
}
