import { Badge } from './Badge'
import { cn } from '@/shared/lib/utils'
import { formatCurrencyBRL, formatPercent } from '@/shared/lib/format'

type Props = {
  precoOriginal: string
  precoPromocional?: string | null
  descontoPercentual?: string | null
  className?: string
}

// Exibe o preço de uma variante, com destaque de promoção quando aplicável.
// O preço promocional SEMPRE vem pronto da API (preco_promocional já
// calculado pelo backend) — este componente nunca recalcula o desconto,
// apenas formata os valores recebidos (ver docs/openapi.yaml VarianteResponse).
export function PrecoPromocional({ precoOriginal, precoPromocional, descontoPercentual, className }: Props) {
  if (!precoPromocional) {
    return <span className={cn('font-medium text-text', className)}>{formatCurrencyBRL(precoOriginal)}</span>
  }

  return (
    <span className={cn('inline-flex flex-wrap items-center gap-1.5', className)}>
      <span className="text-xs text-text-muted line-through">{formatCurrencyBRL(precoOriginal)}</span>
      <span className="font-semibold text-primary">{formatCurrencyBRL(precoPromocional)}</span>
      {descontoPercentual && <Badge tone="primary">-{formatPercent(descontoPercentual)}</Badge>}
    </span>
  )
}
