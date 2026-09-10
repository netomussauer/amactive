import { Link } from 'react-router-dom'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Badge } from '@/shared/components/ui/Badge'
import { Spinner } from '@/shared/components/ui/Spinner'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { routes } from '@/shared/lib/routes'
import { useAlertasEstoque } from '@/features/estoque'

export function AlertaEstoqueList() {
  const { data, isLoading } = useAlertasEstoque()

  return (
    <Card>
      <CardHeader>
        <CardTitle>Alertas de estoque baixo</CardTitle>
        <Link to={routes.estoque} className="text-sm font-medium text-primary hover:underline">
          Ver estoque
        </Link>
      </CardHeader>

      {isLoading && <Spinner label="Carregando alertas..." />}

      {!isLoading && (data?.data.length ?? 0) === 0 && (
        <EmptyState title="Nenhum alerta de estoque" description="Todos os SKUs estão com saldo saudável." />
      )}

      {!isLoading && (data?.data.length ?? 0) > 0 && (
        <ul className="divide-y divide-border">
          {data?.data.slice(0, 6).map((item) => (
            <li key={item.variante_id} className="flex items-center justify-between py-2 text-sm">
              <div>
                <p className="font-medium text-text">{item.produto_nome}</p>
                <p className="text-xs text-text-muted">SKU {item.sku}</p>
              </div>
              <Badge tone={item.quantidade <= 0 ? 'critico' : 'baixo'}>{item.quantidade} un.</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
