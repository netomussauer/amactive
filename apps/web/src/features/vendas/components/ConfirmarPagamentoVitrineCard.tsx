import { useState } from 'react'
import { Button } from '@/shared/components/ui/Button'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { FormField } from '@/shared/components/ui/FormField'
import { Select } from '@/shared/components/ui/Select'
import { formatCurrencyBRL, formatDateTime } from '@/shared/lib/format'
import type { FormaPagamento, PedidoDetalhe } from '../types/pedido.types'
import { useConfirmarPagamentoVitrine } from '../hooks/useConfirmarPagamentoVitrine'

// Formas recebidas diretamente pela loja. NUVEMSHOP não se aplica à vitrine.
const FORMAS: ReadonlyArray<{ value: FormaPagamento; label: string }> = [
  { value: 'PIX', label: 'PIX' },
  { value: 'DINHEIRO', label: 'Dinheiro' },
  { value: 'CARTAO_DEBITO', label: 'Cartão de débito' },
  { value: 'CARTAO_CREDITO', label: 'Cartão de crédito' },
]

type Props = { pedido: PedidoDetalhe }

// Ação exclusiva de pedido da loja online ainda PENDENTE: a equipe registra o
// pagamento recebido pelo WhatsApp. É esta confirmação que baixa o estoque.
export function ConfirmarPagamentoVitrineCard({ pedido }: Props) {
  const [forma, setForma] = useState<FormaPagamento>('PIX')
  const { mutate, isPending } = useConfirmarPagamentoVitrine()

  function confirmar() {
    const mensagem = `Confirmar o pagamento de ${formatCurrencyBRL(pedido.valor_total)} (${forma}) do pedido ${pedido.numero}? O estoque será baixado.`
    if (!window.confirm(mensagem)) return
    mutate({ id: pedido.id, pagamentos: [{ forma_pagamento: forma, valor: pedido.valor_total }] })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Confirmar pagamento</CardTitle>
      </CardHeader>
      <p className="text-sm text-text-muted">
        Confirme somente depois de receber o pagamento pelo WhatsApp. Ao confirmar, as peças saem do estoque.
        {pedido.reservado_ate && <> A reserva vale até {formatDateTime(pedido.reservado_ate)}.</>}
      </p>
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
        <FormField label="Forma de pagamento" htmlFor="forma-pagamento-vitrine">
          <Select
            id="forma-pagamento-vitrine"
            value={forma}
            onChange={(e) => setForma(e.target.value as FormaPagamento)}
          >
            {FORMAS.map((opcao) => (
              <option key={opcao.value} value={opcao.value}>
                {opcao.label}
              </option>
            ))}
          </Select>
        </FormField>
        <p className="text-sm">
          Valor: <strong className="text-text">{formatCurrencyBRL(pedido.valor_total)}</strong>
        </p>
        <Button isLoading={isPending} onClick={confirmar}>
          Confirmar pagamento
        </Button>
      </div>
    </Card>
  )
}
