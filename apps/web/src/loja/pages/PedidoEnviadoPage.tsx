import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { Copy } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Textarea } from '@/shared/components/ui/Textarea'
import { formatCurrencyBRL, formatDateTime } from '@/shared/lib/format'
import { toast } from '@/shared/lib/toast'
import type { PedidoCheckoutLoja } from '../schemas/loja.schema'
import { WHATSAPP_LOJA } from '../config'
import { linkWhatsApp, montarMensagemPedido } from '../lib/mensagem-pedido'

type EstadoNavegacao = { pedido: PedidoCheckoutLoja; nomeCliente: string }

export function PedidoEnviadoPage() {
  const location = useLocation()
  const estado = location.state as EstadoNavegacao | null

  // Sem o estado da navegação (ex.: recarregamento da aba), não há pedido para
  // mostrar. Voltamos à vitrine em vez de exibir uma tela vazia.
  if (!estado?.pedido) return <Navigate to="/" replace />

  return <ConfirmacaoPedido pedido={estado.pedido} nomeCliente={estado.nomeCliente} />
}

function ConfirmacaoPedido({ pedido, nomeCliente }: EstadoNavegacao) {
  const mensagem = montarMensagemPedido({
    numero: pedido.numero,
    nomeCliente,
    itens: pedido.itens.map((item) => ({
      descricao: item.descricao,
      quantidade: item.quantidade,
      subtotal: item.subtotal,
    })),
    valorTotal: pedido.valor_total,
  })
  const link = linkWhatsApp(WHATSAPP_LOJA, mensagem)
  const [copiado, setCopiado] = useState(false)

  async function copiarMensagem() {
    try {
      await navigator.clipboard.writeText(mensagem)
      setCopiado(true)
      toast.success('Mensagem copiada')
    } catch {
      // Clipboard indisponível (permissão negada ou contexto não seguro): o
      // texto continua visível no campo abaixo para copiar manualmente.
      toast.error('Não foi possível copiar. Selecione o texto e copie manualmente.')
    }
  }

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6">
      <section className="flex flex-col gap-2">
        <p className="text-sm font-medium text-primary">Pedido {pedido.numero} registrado</p>
        <h1 className="font-sans text-2xl font-semibold text-text">Falta um passo: envie o pedido pelo WhatsApp</h1>
        <p className="text-sm text-text-muted">
          Suas peças estão reservadas até {formatDateTime(pedido.reservado_ate)}. A equipe confirma o pagamento e a
          entrega com você pelo WhatsApp.
        </p>
      </section>

      <ul className="flex flex-col divide-y divide-border rounded-lg border border-border text-sm">
        {pedido.itens.map((item) => (
          <li key={item.sku} className="flex items-center justify-between gap-4 p-3">
            <span>
              {item.quantidade}x {item.descricao}
            </span>
            <span className="font-medium">{formatCurrencyBRL(item.subtotal)}</span>
          </li>
        ))}
        <li className="flex items-center justify-between gap-4 p-3 font-semibold">
          <span>Total</span>
          <span>{formatCurrencyBRL(pedido.valor_total)}</span>
        </li>
      </ul>

      {link ? (
        <a
          href={link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex h-12 items-center justify-center rounded-md bg-primary px-6 text-base font-medium text-white hover:bg-primary-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2"
        >
          Enviar pedido pelo WhatsApp
        </a>
      ) : (
        <p className="rounded-md border border-border bg-bg-subtle p-3 text-sm text-text-muted">
          O envio direto pelo WhatsApp ainda não está disponível. Copie a mensagem abaixo e envie para a loja.
        </p>
      )}

      <div className="flex flex-col gap-2">
        <label htmlFor="mensagem-pedido" className="text-sm font-medium">
          Mensagem do pedido
        </label>
        <Textarea id="mensagem-pedido" readOnly rows={8} value={mensagem} className="font-mono text-xs" />
        <div>
          <Button variant="outline" onClick={copiarMensagem}>
            <Copy className="h-4 w-4" aria-hidden="true" />
            {copiado ? 'Mensagem copiada' : 'Copiar mensagem'}
          </Button>
        </div>
      </div>
    </div>
  )
}
