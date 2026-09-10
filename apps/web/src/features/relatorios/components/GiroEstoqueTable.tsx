import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import type { GiroEstoqueItem } from '../types/relatorio.types'

type Props = {
  itens: GiroEstoqueItem[]
  isLoading: boolean
}

export function GiroEstoqueTable({ itens, isLoading }: Props) {
  if (isLoading) return <TableSkeleton cols={3} />

  if (itens.length === 0) {
    return <EmptyState title="Sem dados de giro de estoque" description="Ajuste o período para ver o giro por variante." />
  }

  return (
    <Table aria-label="Giro de estoque por variante">
      <TableHead>
        <TableRow>
          <TableHeadCell>SKU</TableHeadCell>
          <TableHeadCell>Saídas no período</TableHeadCell>
          <TableHeadCell>Saldo atual</TableHeadCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {itens.map((item) => (
          <TableRow key={item.variante_id}>
            <TableCell className="font-mono text-xs">{item.sku}</TableCell>
            <TableCell>{item.total_saidas}</TableCell>
            <TableCell>{item.saldo_atual}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
