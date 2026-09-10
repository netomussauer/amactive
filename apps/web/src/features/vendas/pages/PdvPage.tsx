import { useMemo, useState } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Button } from '@/shared/components/ui/Button'
import { formatCurrencyBRL } from '@/shared/lib/format'
import { PdvBuscaProduto } from '../components/PdvBuscaProduto'
import { PdvCarrinho, calcularSubtotalItem } from '../components/PdvCarrinho'
import { PdvPagamentoForm } from '../components/PdvPagamentoForm'
import { useCarrinhoStore } from '../store/carrinho.store'
import type { PedidoDetalhe } from '../schemas/pedido.schema'

// Página do PDV: orquestra busca, carrinho, pagamento e confirmação da venda.
export function PdvPage() {
  const itens = useCarrinhoStore((state) => state.itens)
  const clear = useCarrinhoStore((state) => state.clear)
  const [pedidoConfirmado, setPedidoConfirmado] = useState<PedidoDetalhe | null>(null)

  const subtotal = useMemo(
    () => itens.reduce((acc, item) => acc + calcularSubtotalItem(item.precoUnitario, item.quantidade, item.descontoItem), 0),
    [itens],
  )

  function handleConfirmado(pedido: PedidoDetalhe) {
    setPedidoConfirmado(pedido)
    clear()
  }

  function handleNovaVenda() {
    setPedidoConfirmado(null)
  }

  if (pedidoConfirmado) {
    return (
      <PageWrapper title="PDV — Nova venda" description="Venda confirmada com sucesso.">
        <Card className="mx-auto max-w-md text-center">
          <CheckCircle2 className="mx-auto h-12 w-12 text-status-ok" aria-hidden="true" />
          <h2 className="mt-3 font-sans text-xl font-bold text-text">Venda confirmada!</h2>
          <p className="mt-1 text-sm text-text-muted">Pedido {pedidoConfirmado.numero}</p>
          <p className="mt-4 font-sans text-2xl font-bold text-primary">{formatCurrencyBRL(pedidoConfirmado.valor_total)}</p>
          <Button className="mt-6 w-full" onClick={handleNovaVenda}>
            Nova venda
          </Button>
        </Card>
      </PageWrapper>
    )
  }

  return (
    <PageWrapper title="PDV — Nova venda" description="Busque produtos por SKU ou nome para montar a venda.">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Buscar produto</CardTitle>
          </CardHeader>
          <PdvBuscaProduto />
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Carrinho</CardTitle>
            </CardHeader>
            <PdvCarrinho />
          </Card>

          {itens.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Pagamento</CardTitle>
              </CardHeader>
              <PdvPagamentoForm subtotal={subtotal} onConfirmado={handleConfirmado} />
            </Card>
          )}
        </div>
      </div>
    </PageWrapper>
  )
}
