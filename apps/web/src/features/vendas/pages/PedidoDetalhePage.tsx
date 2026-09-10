import { useParams } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Button } from '@/shared/components/ui/Button'
import { Spinner } from '@/shared/components/ui/Spinner'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { PedidoDetalheCard } from '../components/PedidoDetalheCard'
import { usePedido } from '../hooks/usePedido'
import { useCancelarPedido } from '../hooks/useCancelarPedido'

// Detalhe do pedido, com ação de cancelamento.
export function PedidoDetalhePage() {
  const { pedidoId } = useParams<{ pedidoId: string }>()
  const { data: pedido, isLoading } = usePedido(pedidoId)
  const { mutate: cancelar, isPending } = useCancelarPedido()

  if (isLoading) {
    return (
      <PageWrapper title="Pedido">
        <Spinner label="Carregando pedido..." />
      </PageWrapper>
    )
  }

  if (!pedido) {
    return (
      <PageWrapper title="Pedido">
        <EmptyState title="Pedido não encontrado" description="Verifique o endereço ou volte para a lista de pedidos." />
      </PageWrapper>
    )
  }

  const podeCancelar = pedido.status !== 'CANCELADO'

  return (
    <PageWrapper
      title={`Pedido ${pedido.numero}`}
      description="Detalhe completo da venda."
      actions={
        podeCancelar ? (
          <Button
            variant="danger"
            isLoading={isPending}
            onClick={() => {
              if (window.confirm(`Cancelar o pedido ${pedido.numero}? Esta ação não pode ser desfeita.`)) {
                cancelar(pedido.id)
              }
            }}
          >
            Cancelar pedido
          </Button>
        ) : undefined
      }
    >
      <PedidoDetalheCard pedido={pedido} />
    </PageWrapper>
  )
}
