import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Button, Input, Pagination } from '@/shared/components/ui'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { routes } from '@/shared/lib/routes'
import { ClienteTable } from '../components/ClienteTable'
import { useClientes } from '../hooks/useClientes'

export function ClientesListPage() {
  const navigate = useNavigate()
  const [busca, setBusca] = useState('')
  const [page, setPage] = useState(1)
  const buscaDebounced = useDebounce(busca)

  const { data, isLoading } = useClientes({ busca: buscaDebounced || undefined, page, per_page: 20 })

  return (
    <PageWrapper
      title="Clientes"
      description="Cadastro de clientes da AMACTIVE."
      actions={
        <Button onClick={() => navigate(routes.clienteNovo)}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          Novo cliente
        </Button>
      }
    >
      <div className="mb-4 max-w-sm">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" aria-hidden="true" />
          <Input
            aria-label="Buscar cliente por nome, e-mail ou CPF/CNPJ"
            placeholder="Buscar cliente..."
            className="pl-9"
            value={busca}
            onChange={(event) => {
              setBusca(event.target.value)
              setPage(1)
            }}
          />
        </div>
      </div>

      <ClienteTable clientes={data?.data ?? []} isLoading={isLoading} />

      {data && <Pagination pagination={data.pagination} onPageChange={setPage} />}
    </PageWrapper>
  )
}
