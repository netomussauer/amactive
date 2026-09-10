import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import { formatCurrencyBRL } from '@/shared/lib/format'
import type { ProdutoMaisVendido } from '../types/relatorio.types'

type Props = {
  produtos: ProdutoMaisVendido[]
  isLoading: boolean
}

export function ProdutosMaisVendidosTable({ produtos, isLoading }: Props) {
  if (isLoading) return <TableSkeleton cols={4} />

  if (produtos.length === 0) {
    return <EmptyState title="Sem vendas no período" description="Ajuste o período para ver o ranking de produtos." />
  }

  return (
    <Table aria-label="Produtos mais vendidos">
      <TableHead>
        <TableRow>
          <TableHeadCell>SKU</TableHeadCell>
          <TableHeadCell>Produto</TableHeadCell>
          <TableHeadCell>Qtd. vendida</TableHeadCell>
          <TableHeadCell className="text-right">Faturamento</TableHeadCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {produtos.map((produto) => (
          <TableRow key={produto.variante_id}>
            <TableCell className="font-mono text-xs">{produto.sku}</TableCell>
            <TableCell className="font-medium">{produto.produto_nome}</TableCell>
            <TableCell>{produto.quantidade_vendida}</TableCell>
            <TableCell className="text-right">{formatCurrencyBRL(produto.faturamento)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
