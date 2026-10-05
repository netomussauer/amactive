// Mensagem de fechamento do pedido pelo WhatsApp da loja. O pagamento não passa
// pelo sistema: o cliente envia este resumo e a equipe combina a cobrança.

import { formatCurrencyBRL } from '@/shared/lib/format'

export type ItemMensagem = {
  descricao: string
  quantidade: number
  subtotal: string
}

export type DadosMensagemPedido = {
  numero: string
  nomeCliente: string
  itens: ItemMensagem[]
  valorTotal: string
}

export function montarMensagemPedido(dados: DadosMensagemPedido): string {
  const linhas = dados.itens.map(
    (item) =>
      `• ${item.quantidade}x ${item.descricao} — ${formatCurrencyBRL(item.subtotal)}`,
  )
  return [
    'Olá! Quero finalizar meu pedido da loja online AMACTIVE.',
    '',
    `Pedido: ${dados.numero}`,
    `Cliente: ${dados.nomeCliente}`,
    '',
    ...linhas,
    '',
    `Total: ${formatCurrencyBRL(dados.valorTotal)}`,
    '',
    'Pode me passar a forma de pagamento?',
  ].join('\n')
}

/**
 * Link `wa.me` com a mensagem pronta. Retorna null sem número configurado —
 * a tela, então, oferece copiar a mensagem em vez de um link quebrado.
 */
export function linkWhatsApp(numero: string, mensagem: string): string | null {
  const digitos = numero.replace(/\D/g, '')
  if (!digitos) return null
  return `https://wa.me/${digitos}?text=${encodeURIComponent(mensagem)}`
}
