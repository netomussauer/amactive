import type { MouseEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Badge } from '@/shared/components/ui/Badge'
import { Button } from '@/shared/components/ui/Button'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import { routes } from '@/shared/lib/routes'
import { PAPEL_LABELS } from '../lib/papel-labels'
import { useInativarUsuario } from '../hooks/useInativarUsuario'
import { useReativarUsuario } from '../hooks/useReativarUsuario'
import type { UsuarioDetalhe } from '../types/usuario.types'

type Props = {
  usuarios: UsuarioDetalhe[]
  isLoading?: boolean
}

export function UsuarioTable({ usuarios, isLoading }: Props) {
  const navigate = useNavigate()
  const { mutate: inativar } = useInativarUsuario()
  const { mutate: reativar } = useReativarUsuario()

  if (isLoading) return <TableSkeleton cols={5} />

  if (usuarios.length === 0) {
    return (
      <EmptyState
        title="Nenhum usuário cadastrado ainda"
        description="Cadastre o primeiro usuário com acesso ao sistema."
      />
    )
  }

  function handleToggleAtivo(event: MouseEvent, usuario: UsuarioDetalhe) {
    event.stopPropagation()
    if (usuario.ativo) {
      // Mesmo padrão de confirmação já usado em Clientes/Fornecedores/Produtos
      // antes de uma ação destrutiva. Salvaguarda do backend: não é possível
      // desativar o único ADMIN ativo do sistema (409, tratado globalmente).
      if (window.confirm(`Desativar o usuário ${usuario.nome}?`)) inativar(usuario.id)
      return
    }
    reativar({ id: usuario.id, nome: usuario.nome, papel: usuario.papel })
  }

  return (
    <Table aria-label="Lista de usuários">
      <TableHead>
        <TableRow>
          <TableHeadCell>Nome</TableHeadCell>
          <TableHeadCell>E-mail</TableHeadCell>
          <TableHeadCell>Papel</TableHeadCell>
          <TableHeadCell>Status</TableHeadCell>
          <TableHeadCell className="text-right">Ações</TableHeadCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {usuarios.map((usuario) => (
          <TableRow
            key={usuario.id}
            className="cursor-pointer"
            onClick={() => navigate(routes.usuarioDetalhe(usuario.id))}
          >
            <TableCell className="font-medium">{usuario.nome}</TableCell>
            <TableCell>{usuario.email}</TableCell>
            <TableCell>{PAPEL_LABELS[usuario.papel]}</TableCell>
            <TableCell>
              <Badge tone={usuario.ativo ? 'ok' : 'neutral'}>{usuario.ativo ? 'Ativo' : 'Inativo'}</Badge>
            </TableCell>
            <TableCell className="text-right">
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(event) => {
                    event.stopPropagation()
                    navigate(routes.usuarioDetalhe(usuario.id))
                  }}
                >
                  Editar
                </Button>
                <Button variant="ghost" size="sm" onClick={(event) => handleToggleAtivo(event, usuario)}>
                  {usuario.ativo ? 'Desativar' : 'Reativar'}
                </Button>
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
