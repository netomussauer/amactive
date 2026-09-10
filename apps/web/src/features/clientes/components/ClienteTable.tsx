import { useNavigate } from 'react-router-dom'
import { Badge } from '@/shared/components/ui/Badge'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import { routes } from '@/shared/lib/routes'
import type { Cliente } from '../types/cliente.types'

type Props = {
  clientes: Cliente[]
  isLoading?: boolean
}

export function ClienteTable({ clientes, isLoading }: Props) {
  const navigate = useNavigate()

  if (isLoading) return <TableSkeleton cols={4} />

  if (clientes.length === 0) {
    return (
      <EmptyState title="Nenhum cliente cadastrado ainda" description="Cadastre o primeiro cliente da AMACTIVE." />
    )
  }

  return (
    <Table aria-label="Lista de clientes">
      <TableHead>
        <TableRow>
          <TableHeadCell>Nome</TableHeadCell>
          <TableHeadCell>Telefone</TableHeadCell>
          <TableHeadCell>E-mail</TableHeadCell>
          <TableHeadCell>Status</TableHeadCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {clientes.map((cliente) => (
          <TableRow key={cliente.id} className="cursor-pointer" onClick={() => navigate(routes.clienteDetalhe(cliente.id))}>
            <TableCell className="font-medium">{cliente.nome}</TableCell>
            <TableCell>{cliente.telefone || '—'}</TableCell>
            <TableCell>{cliente.email || '—'}</TableCell>
            <TableCell>
              <Badge tone={cliente.ativo ? 'ok' : 'neutral'}>{cliente.ativo ? 'Ativo' : 'Inativo'}</Badge>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
