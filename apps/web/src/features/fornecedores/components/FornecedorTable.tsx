import { useNavigate } from 'react-router-dom'
import { Badge } from '@/shared/components/ui/Badge'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import { routes } from '@/shared/lib/routes'
import type { Fornecedor } from '../types/fornecedor.types'

type Props = {
  fornecedores: Fornecedor[]
  isLoading?: boolean
}

export function FornecedorTable({ fornecedores, isLoading }: Props) {
  const navigate = useNavigate()

  if (isLoading) return <TableSkeleton cols={4} />

  if (fornecedores.length === 0) {
    return <EmptyState title="Nenhum fornecedor cadastrado ainda" description="Cadastre o primeiro fornecedor." />
  }

  return (
    <Table aria-label="Lista de fornecedores">
      <TableHead>
        <TableRow>
          <TableHeadCell>Razão social</TableHeadCell>
          <TableHeadCell>Nome fantasia</TableHeadCell>
          <TableHeadCell>Telefone</TableHeadCell>
          <TableHeadCell>Status</TableHeadCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {fornecedores.map((fornecedor) => (
          <TableRow
            key={fornecedor.id}
            className="cursor-pointer"
            onClick={() => navigate(routes.fornecedorDetalhe(fornecedor.id))}
          >
            <TableCell className="font-medium">{fornecedor.razao_social}</TableCell>
            <TableCell>{fornecedor.nome_fantasia || '—'}</TableCell>
            <TableCell>{fornecedor.telefone || '—'}</TableCell>
            <TableCell>
              <Badge tone={fornecedor.ativo ? 'ok' : 'neutral'}>{fornecedor.ativo ? 'Ativo' : 'Inativo'}</Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
