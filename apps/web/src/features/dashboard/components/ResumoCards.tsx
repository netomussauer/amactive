import { DollarSign, Receipt, TrendingUp, AlertTriangle } from 'lucide-react'
import { Card } from '@/shared/components/ui/Card'
import { Skeleton } from '@/shared/components/ui/Skeleton'
import { formatCurrencyBRL } from '@/shared/lib/format'
import type { DashboardResumo } from '../types/dashboard.types'

type Props = {
  resumo: DashboardResumo | undefined
  isLoading: boolean
}

export function ResumoCards({ resumo, isLoading }: Props) {
  const cards = [
    {
      label: 'Faturamento no período',
      value: resumo ? formatCurrencyBRL(resumo.faturamento_periodo) : '—',
      icon: DollarSign,
    },
    {
      label: 'Pedidos no período',
      value: resumo ? String(resumo.total_pedidos_periodo) : '—',
      icon: Receipt,
    },
    {
      label: 'Ticket médio',
      value: resumo ? formatCurrencyBRL(resumo.ticket_medio) : '—',
      icon: TrendingUp,
    },
    {
      label: 'Variantes em alerta',
      value: resumo ? String(resumo.variantes_em_alerta_estoque) : '—',
      icon: AlertTriangle,
      warn: (resumo?.variantes_em_alerta_estoque ?? 0) > 0,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map(({ label, value, icon: Icon, warn }) => (
        <Card key={label}>
          <div className="flex items-center justify-between">
            <p className="text-sm text-text-muted">{label}</p>
            <Icon className={warn ? 'h-4 w-4 text-status-baixo' : 'h-4 w-4 text-primary'} aria-hidden="true" />
          </div>
          {isLoading ? (
            <Skeleton className="mt-2 h-8 w-24" />
          ) : (
            <p className="mt-1 font-sans text-2xl font-bold text-text">{value}</p>
          )}
        </Card>
      ))}
    </div>
  )
}
