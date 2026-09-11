// Helpers de formatação — a API trafega valores monetários como string decimal
// fixa (ex: "129.90") para evitar problemas de ponto flutuante. Ver
// docs/openapi.yaml (pattern '^\d+\.\d{2}$').

export function formatCurrencyBRL(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return 'R$ 0,00'
  const numeric = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(numeric)) return 'R$ 0,00'
  return numeric.toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  })
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleDateString('pt-BR')
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
}

// Converte number para o formato "0.00" exigido pela API em campos monetários.
export function toDecimalString(value: number): string {
  return value.toFixed(2)
}

// Formata um percentual (ex: variante.desconto_percentual = "15.00") para
// exibição, sem casas decimais desnecessárias (ex: "15%", "12,5%").
export function formatPercent(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '0%'
  const numeric = typeof value === 'string' ? Number(value) : value
  if (Number.isNaN(numeric)) return '0%'
  const semZerosSobrando = Number(numeric.toFixed(2))
  return `${semZerosSobrando.toLocaleString('pt-BR')}%`
}
