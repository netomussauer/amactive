import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import { AlertaEstoqueBadge } from './AlertaEstoqueBadge'
import type { EstoqueItem } from '../types/estoque.types'

type Props = {
  itens: EstoqueItem[]
  isLoading?: boolean
}

export function EstoqueTable({ itens, isLoading }: Props) {
  if (isLoading) return <TableSkeleton cols={5} />

  if (itens.length === 0) {
    return <EmptyState title="Nenhum saldo de estoque encontrado" description="Ajuste os filtros ou cadastre variantes de produto." />
  }

  return (
    <Table aria-label="Saldo de estoque por variante">
      <TableHead>
        <TableRow>
          <TableHeadCell>SKU</TableHeadCell>
          <TableHeadCell>Produto</TableHeadCell>
          <TableHeadCell>Quantidade</TableHeadCell>
          <TableHeadCell>Mínimo</TableHeadCell>
          <TableHeadCell>Situação</TableHeadCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {itens.map((item) => (
          <TableRow key={item.variante_id}>
            <TableCell className="font-mono text-xs">{item.sku}</TableCell>
            <TableCell className="font-medium">{item.produto_nome}</TableCell>
            <TableCell>{item.quantidade}</TableCell>
            <TableCell>{item.estoque_minimo}</TableCell>
            <TableCell>
              <AlertaEstoqueBadge quantidade={item.quantidade} emAlerta={item.em_alerta} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
