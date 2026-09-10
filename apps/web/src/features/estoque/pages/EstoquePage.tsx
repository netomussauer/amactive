import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, History } from 'lucide-react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Button, Input, Pagination } from '@/shared/components/ui'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { cn } from '@/shared/lib/utils'
import { routes } from '@/shared/lib/routes'
import { EstoqueTable } from '../components/EstoqueTable'
import { useEstoque } from '../hooks/useEstoque'
import { useAlertasEstoque } from '../hooks/useAlertasEstoque'

type Tab = 'todos' | 'alertas'

// Saldo de estoque por variante, com aba de alertas de estoque baixo.
export function EstoquePage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('todos')
  const [sku, setSku] = useState('')
  const [page, setPage] = useState(1)
  const skuDebounced = useDebounce(sku)

  const listQuery = useEstoque({ sku: skuDebounced || undefined, page, per_page: 20 })
  const alertasQuery = useAlertasEstoque()

  const isAlertasTab = tab === 'alertas'
  const itens = isAlertasTab ? alertasQuery.data?.data ?? [] : listQuery.data?.data ?? []
  const isLoading = isAlertasTab ? alertasQuery.isLoading : listQuery.isLoading

  return (
    <PageWrapper
      title="Estoque"
      description="Saldo de estoque por variante (SKU) e alertas de estoque baixo."
      actions={
        <Button variant="outline" onClick={() => navigate(routes.estoqueMovimentacoes)}>
          <History className="h-4 w-4" aria-hidden="true" />
          Movimentações
        </Button>
      }
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div role="tablist" aria-label="Filtro de estoque" className="flex gap-1 rounded-md border border-border bg-bg p-1">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'todos'}
            className={cn('rounded px-3 py-1.5 text-sm font-medium', tab === 'todos' ? 'bg-primary text-white' : 'text-text-muted')}
            onClick={() => setTab('todos')}
          >
            Todos
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'alertas'}
            className={cn('rounded px-3 py-1.5 text-sm font-medium', tab === 'alertas' ? 'bg-primary text-white' : 'text-text-muted')}
            onClick={() => setTab('alertas')}
          >
            Alertas de estoque baixo
          </button>
        </div>

        {!isAlertasTab && (
          <div className="relative w-full max-w-xs">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" aria-hidden="true" />
            <Input
              aria-label="Buscar por SKU"
              placeholder="Buscar por SKU..."
              className="pl-9"
              value={sku}
              onChange={(event) => {
                setSku(event.target.value)
                setPage(1)
              }}
            />
          </div>
        )}
      </div>

      <EstoqueTable itens={itens} isLoading={isLoading} />

      {!isAlertasTab && listQuery.data && <Pagination pagination={listQuery.data.pagination} onPageChange={setPage} />}
    </PageWrapper>
  )
}
