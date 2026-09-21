import { Badge } from '@/shared/components/ui/Badge'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { formatCurrencyBRL, formatDateTime } from '@/shared/lib/format'
import type { PedidoDetalhe, StatusPedido } from '../types/pedido.types'
import { labelPedidoExterno } from '../lib/canal'
import { CanalBadge } from './CanalBadge'

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

const formaPagamentoLabel: Record<string, string> = {
  DINHEIRO: 'Dinheiro',
  PIX: 'PIX',
  CARTAO_DEBITO: 'Cartão de débito',
  CARTAO_CREDITO: 'Cartão de crédito',
  NUVEMSHOP: 'Nuvemshop (pago no checkout)',
}

type Props = {
  pedido: PedidoDetalhe
}

export function PedidoDetalheCard({ pedido }: Props) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div>
            <CardTitle>Pedido {pedido.numero}</CardTitle>
            <p className="text-sm text-text-muted">{formatDateTime(pedido.criado_em)}</p>
          </div>
          <div className="flex flex-wrap items-center justify-end gap-2">
            <CanalBadge canal={pedido.origem_canal} />
            <Badge tone={statusTone[pedido.status]}>{statusLabel[pedido.status]}</Badge>
          </div>
        </CardHeader>
        <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          {pedido.pedido_externo_id && (
            <div>
              <p className="text-text-muted">{labelPedidoExterno(pedido.origem_canal)}</p>
              <p className="font-medium text-text">{pedido.pedido_externo_id}</p>
            </div>
          )}
          <div>
            <p className="text-text-muted">Subtotal</p>
            <p className="font-medium text-text">{formatCurrencyBRL(pedido.subtotal)}</p>
          </div>
          <div>
            <p className="text-text-muted">Desconto</p>
            <p className="font-medium text-text">{formatCurrencyBRL(pedido.desconto)}</p>
          </div>
          <div>
            <p className="text-text-muted">Total</p>
            <p className="font-medium text-text">{formatCurrencyBRL(pedido.valor_total)}</p>
          </div>
          <div>
            <p className="text-text-muted">Confirmado em</p>
            <p className="font-medium text-text">{formatDateTime(pedido.confirmado_em)}</p>
          </div>
        </div>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Itens</CardTitle>
        </CardHeader>
        <Table aria-label={`Itens do pedido ${pedido.numero}`}>
          <TableHead>
            <TableRow>
              <TableHeadCell>SKU</TableHeadCell>
              <TableHeadCell>Quantidade</TableHeadCell>
              <TableHeadCell>Preço unitário</TableHeadCell>
              <TableHeadCell className="text-right">Subtotal</TableHeadCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {pedido.itens.map((item) => (
              <TableRow key={item.id}>
                <TableCell className="font-mono text-xs">{item.sku}</TableCell>
                <TableCell>{item.quantidade}</TableCell>
                <TableCell>{formatCurrencyBRL(item.preco_unitario)}</TableCell>
                <TableCell className="text-right">{formatCurrencyBRL(item.subtotal)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Pagamentos</CardTitle>
        </CardHeader>
        <ul className="divide-y divide-border">
          {pedido.pagamentos.map((pagamento) => (
            <li key={pagamento.id} className="flex items-center justify-between py-2 text-sm">
              <span>{formaPagamentoLabel[pagamento.forma_pagamento] ?? pagamento.forma_pagamento}</span>
              <span className="font-medium text-text">{formatCurrencyBRL(pagamento.valor)}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
