import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Button, Input, Pagination } from '@/shared/components/ui'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { routes } from '@/shared/lib/routes'
import { ProdutoTable } from '../components/ProdutoTable'
import { useProdutos } from '../hooks/useProdutos'

export function ProdutosListPage() {
  const navigate = useNavigate()
  const [busca, setBusca] = useState('')
  const [page, setPage] = useState(1)
  const buscaDebounced = useDebounce(busca)

  const { data, isLoading } = useProdutos({ busca: buscaDebounced || undefined, page, per_page: 20 })

  return (
    <PageWrapper
      title="Produtos"
      description="Catálogo de produtos e variantes (SKUs) da AMACTIVE."
      actions={
        <Button onClick={() => navigate(routes.produtoNovo)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Novo produto
        </Button>
      }
    >
      <div className="mb-4 max-w-sm">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" aria-hidden="true" />
          <Input
            aria-label="Buscar produto por nome"
            placeholder="Buscar por nome..."
            className="pl-9"
            value={busca}
            onChange={(event) => {
              setBusca(event.target.value)
              setPage(1)
            }}
          />
        </div>
      </div>

      <ProdutoTable produtos={data?.data ?? []} isLoading={isLoading} />

      {data && <Pagination pagination={data.pagination} onPageChange={setPage} />}
    </PageWrapper>
  )
}
