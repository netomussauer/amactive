import { useState } from 'react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Input } from '@/shared/components/ui/Input'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { formatCurrencyBRL } from '@/shared/lib/format'
import { ResumoCards } from '../components/ResumoCards'
import { AlertaEstoqueList } from '../components/AlertaEstoqueList'
import { useDashboardResumo } from '../hooks/useDashboardResumo'

function primeiroDiaDoMes(): string {
  const hoje = new Date()
  return new Date(hoje.getFullYear(), hoje.getMonth(), 1).toISOString().slice(0, 10)
}

function hojeISO(): string {
  return new Date().toISOString().slice(0, 10)
}

// Painel inicial com indicadores de vendas e estoque.
export function DashboardPage() {
  const [dataInicio, setDataInicio] = useState(primeiroDiaDoMes())
  const [dataFim, setDataFim] = useState(hojeISO())

  const { data: resumo, isLoading } = useDashboardResumo({ data_inicio: dataInicio, data_fim: dataFim })

  return (
    <PageWrapper title="Dashboard" description="Indicadores de vendas e estoque da AMACTIVE.">
      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="dashboard-data-inicio" className="mb-1.5 block text-sm font-medium text-text">
            De
          </label>
          <Input id="dashboard-data-inicio" type="date" value={dataInicio} onChange={(event) => setDataInicio(event.target.value)} />
        </div>
        <div>
          <label htmlFor="dashboard-data-fim" className="mb-1.5 block text-sm font-medium text-text">
            Até
          </label>
          <Input id="dashboard-data-fim" type="date" value={dataFim} onChange={(event) => setDataFim(event.target.value)} />
        </div>
      </div>

      <div className="space-y-6">
        <ResumoCards resumo={resumo} isLoading={isLoading} />

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Produtos mais vendidos</CardTitle>
            </CardHeader>
            {(resumo?.top_produtos.length ?? 0) === 0 ? (
              <EmptyState title="Sem vendas no período" description="Ajuste o período ou registre vendas no PDV." />
            ) : (
              <ul className="divide-y divide-border">
                {resumo?.top_produtos.map((produto) => (
                  <li key={produto.variante_id} className="flex items-center justify-between py-2 text-sm">
                    <div>
                      <p className="font-medium text-text">{produto.produto_nome}</p>
                      <p className="text-xs text-text-muted">SKU {produto.sku} · {produto.quantidade_vendida} un.</p>
                    </div>
                    <span className="font-medium text-text">{formatCurrencyBRL(produto.faturamento)}</span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <AlertaEstoqueList />
        </div>
      </div>
    </PageWrapper>
  )
}
