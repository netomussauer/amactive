import { useNavigate } from 'react-router-dom'
import { Badge } from '@/shared/components/ui/Badge'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import { formatCurrencyBRL, formatDateTime } from '@/shared/lib/format'
import { routes } from '@/shared/lib/routes'
import type { Pedido, StatusPedido } from '../types/pedido.types'

type Props = {
  pedidos: Pedido[]
  isLoading?: boolean
}

const statusTone: Record<StatusPedido, 'pendente' | 'confirmado' | 'cancelado'> = {
  PENDENTE: 'pendente',
  CONFIRMADO: 'confirmado',
  CANCELADO: 'cancelado',
}

const statusLabel: Record<StatusPedido, string> = {
  PENDENTE: 'Pendente',
  CONFIRMADO: 'Confirmado',
  CANCELADO: 'Cancelado',
}

export function PedidoTable({ pedidos, isLoading }: Props) {
  const navigate = useNavigate()

  if (isLoading) return <TableSkeleton cols={5} />

  if (pedidos.length === 0) {
    return <EmptyState title="Nenhum pedido encontrado" description="Ajuste os filtros ou registre uma nova venda no PDV." />
  }

  return (
    <Table aria-label="Lista de pedidos">
      <TableHead>
        <TableRow>
          <TableHeadCell>Número</TableHeadCell>
          <TableHeadCell>Data</TableHeadCell>
          <TableHeadCell>Status</TableHeadCell>
          <TableHeadCell className="text-right">Total</TableHeadCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {pedidos.map((pedido) => (
          <TableRow key={pedido.id} className="cursor-pointer" onClick={() => navigate(routes.pedidoDetalhe(pedido.id))}>
            <TableCell className="font-medium">{pedido.numero}</TableCell>
            <TableCell className="text-text-muted">{formatDateTime(pedido.criado_em)}</TableCell>
            <TableCell>
              <Badge tone={statusTone[pedido.status]}>{statusLabel[pedido.status]}</Badge>
            </TableCell>
            <TableCell className="text-right font-medium">{formatCurrencyBRL(pedido.valor_total)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
