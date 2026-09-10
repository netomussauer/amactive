import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from './Button'
import type { Pagination as PaginationData } from '@/shared/types/common.types'

type Props = {
  pagination: PaginationData
  onPageChange: (page: number) => void
}

// Paginação server-side (nunca carregar >100 itens de uma vez — ver
// docs/frontend-architecture.md §6).
export function Pagination({ pagination, onPageChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(pagination.total / pagination.per_page))

  if (totalPages <= 1) return null

  return (
    <div className="mt-4 flex items-center justify-between text-sm text-text-muted">
      <p>
        Página {pagination.page} de {totalPages} · {pagination.total} registro(s)
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={pagination.page <= 1}
          onClick={() => onPageChange(pagination.page - 1)}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
          Anterior
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={pagination.page >= totalPages}
          onClick={() => onPageChange(pagination.page + 1)}
        >
          Próxima
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  )
}
