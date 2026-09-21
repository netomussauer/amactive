import type { OrigemCanal } from '../schemas/pedido.schema'

// Rótulos e opções dos canais de venda — fonte única para PDV, lista, detalhe
// e filtros de relatório. `origem_canal` na resposta é string livre; use
// `labelCanal` (com fallback) para exibir valores desconhecidos sem quebrar.
export const ORIGEM_CANAL_OPTIONS: ReadonlyArray<{ value: OrigemCanal; label: string }> = [
  { value: 'PDV', label: 'PDV' },
  { value: 'WHATSAPP', label: 'WhatsApp' },
  { value: 'NUVEMSHOP', label: 'Nuvemshop' },
]

export function labelCanal(canal: string): string {
  return ORIGEM_CANAL_OPTIONS.find((option) => option.value === canal)?.label ?? canal
}

// Rótulo do número do pedido externo. Só a Nuvemshop usa esse número; o fallback
// existe apenas para exibir dados de outros canais que a API venha a devolver.
export function labelPedidoExterno(canal: string): string {
  return canal === 'NUVEMSHOP' ? 'Nº do pedido na Nuvemshop' : 'Nº do pedido externo'
}
