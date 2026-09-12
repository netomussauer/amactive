import { useState } from 'react'
import { Plus } from 'lucide-react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Button, Select, Pagination } from '@/shared/components/ui'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { TableSkeleton } from '@/shared/components/ui/Skeleton'
import { Badge } from '@/shared/components/ui/Badge'
import { formatDateTime } from '@/shared/lib/format'
import { usePermissoes } from '@/shared/hooks/usePermissoes'
import { MovimentacaoModal } from '../components/MovimentacaoModal'
import { useMovimentacoes } from '../hooks/useMovimentacoes'
import type { TipoMovimentacao } from '../types/estoque.types'

const tipoTone: Record<TipoMovimentacao, 'ok' | 'critico' | 'neutral'> = {
  ENTRADA: 'ok',
  SAIDA: 'critico',
  AJUSTE: 'neutral',
}

export function MovimentacoesPage() {
  const { podeRegistrarMovimentacaoEstoque } = usePermissoes()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [tipo, setTipo] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useMovimentacoes({ tipo: tipo || undefined, page, per_page: 20 })

  return (
    <PageWrapper
      title="Movimentações de estoque"
      description="Histórico de entradas, saídas e ajustes manuais de estoque."
      actions={
        podeRegistrarMovimentacaoEstoque ? (
          <Button onClick={() => setIsModalOpen(true)}>
            <Plus className="h-4 w-4" aria-hidden="true" />
            Nova movimentação
          </Button>
        ) : undefined
      }
    >
      <div className="mb-4 max-w-xs">
        <Select
          aria-label="Filtrar por tipo"
          value={tipo}
          onChange={(event) => {
            setTipo(event.target.value)
            setPage(1)
          }}
        >
          <option value="">Todos os tipos</option>
          <option value="ENTRADA">Entrada</option>
          <option value="SAIDA">Saída</option>
          <option value="AJUSTE">Ajuste</option>
        </Select>
      </div>

      {isLoading ? (
        <TableSkeleton cols={5} />
      ) : (data?.data.length ?? 0) === 0 ? (
        <EmptyState title="Nenhuma movimentação encontrada" description="Registre a primeira movimentação manual de estoque." />
      ) : (
        <Table aria-label="Histórico de movimentações">
          <TableHead>
            <TableRow>
              <TableHeadCell>Data</TableHeadCell>
              <TableHeadCell>SKU</TableHeadCell>
              <TableHeadCell>Tipo</TableHeadCell>
              <TableHeadCell>Quantidade</TableHeadCell>
              <TableHeadCell>Motivo</TableHeadCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {data?.data.map((mov) => (
              <TableRow key={mov.id}>
                <TableCell className="text-text-muted">{formatDateTime(mov.criado_em)}</TableCell>
                <TableCell className="font-mono text-xs">{mov.sku}</TableCell>
                <TableCell>
                  <Badge tone={tipoTone[mov.tipo]}>{mov.tipo}</Badge>
                </TableCell>
                <TableCell>{mov.quantidade}</TableCell>
                <TableCell>{mov.motivo}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}

      {data && <Pagination pagination={data.pagination} onPageChange={setPage} />}

      <MovimentacaoModal open={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </PageWrapper>
  )
}
