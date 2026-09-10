import { useNavigate } from 'react-router-dom'
import { Badge } from '@/shared/components/ui/Badge'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import { routes } from '@/shared/lib/routes'
import type { Produto } from '../types/produto.types'

type Props = {
  produtos: Produto[]
  isLoading?: boolean
}

export function ProdutoTable({ produtos, isLoading }: Props) {
  const navigate = useNavigate()

  if (isLoading) return <TableSkeleton cols={4} />

  if (produtos.length === 0) {
    return (
      <EmptyState
        title="Nenhum produto cadastrado ainda"
        description="Cadastre o primeiro produto para começar a montar o catálogo."
      />
    )
  }

  return (
    <Table aria-label="Lista de produtos">
      <TableHead>
        <TableRow>
          <TableHeadCell>Nome</TableHeadCell>
          <TableHeadCell>Marca</TableHeadCell>
          <TableHeadCell>Status</TableHeadCell>
          <TableHeadCell className="text-right">Cadastrado em</TableHeadCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {produtos.map((produto) => (
          <TableRow
            key={produto.id}
            className="cursor-pointer"
            onClick={() => navigate(routes.produtoDetalhe(produto.id))}
          >
            <TableCell className="font-medium">{produto.nome}</TableCell>
            <TableCell>{produto.marca}</TableCell>
            <TableCell>
              <Badge tone={produto.ativo ? 'ok' : 'neutral'}>{produto.ativo ? 'Ativo' : 'Inativo'}</Badge>
            </TableCell>
            <TableCell className="text-right text-text-muted">
              {new Date(produto.criado_em).toLocaleDateString('pt-BR')}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
