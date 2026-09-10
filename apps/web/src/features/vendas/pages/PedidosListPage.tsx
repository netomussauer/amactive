import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShoppingCart } from 'lucide-react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Button, Select, Input, Pagination } from '@/shared/components/ui'
import { routes } from '@/shared/lib/routes'
import { PedidoTable } from '../components/PedidoTable'
import { usePedidos } from '../hooks/usePedidos'

export function PedidosListPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState('')
  const [dataInicio, setDataInicio] = useState('')
  const [dataFim, setDataFim] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = usePedidos({
    status: status || undefined,
    data_inicio: dataInicio || undefined,
    data_fim: dataFim || undefined,
    page,
    per_page: 20,
  })

  return (
    <PageWrapper
      title="Pedidos"
      description="Histórico de vendas realizadas."
      actions={
        <Button onClick={() => navigate(routes.pdv)}>
          <ShoppingCart className="h-4 w-4" aria-hidden="true" />
          Nova venda
        </Button>
      }
    >
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="w-40">
          <label htmlFor="filtro-status" className="mb-1.5 block text-sm font-medium text-text">
            Status
          </label>
          <Select
            id="filtro-status"
            value={status}
            onChange={(event) => {
              setStatus(event.target.value)
              setPage(1)
            }}
          >
            <option value="">Todos</option>
            <option value="PENDENTE">Pendente</option>
            <option value="CONFIRMADO">Confirmado</option>
            <option value="CANCELADO">Cancelado</option>
          </Select>
        </div>
        <div>
          <label htmlFor="filtro-data-inicio" className="mb-1.5 block text-sm font-medium text-text">
            De
          </label>
          <Input
            id="filtro-data-inicio"
            type="date"
            value={dataInicio}
            onChange={(event) => {
              setDataInicio(event.target.value)
              setPage(1)
            }}
          />
        </div>
        <div>
          <label htmlFor="filtro-data-fim" className="mb-1.5 block text-sm font-medium text-text">
            Até
          </label>
          <Input
            id="filtro-data-fim"
            type="date"
            value={dataFim}
            onChange={(event) => {
              setDataFim(event.target.value)
              setPage(1)
            }}
          />
        </div>
      </div>

      <PedidoTable pedidos={data?.data ?? []} isLoading={isLoading} />

      {data && <Pagination pagination={data.pagination} onPageChange={setPage} />}
    </PageWrapper>
  )
}
