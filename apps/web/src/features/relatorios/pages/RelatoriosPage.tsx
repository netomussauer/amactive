import { useState } from 'react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Input } from '@/shared/components/ui/Input'
import { Select } from '@/shared/components/ui/Select'
import { ORIGEM_CANAL_OPTIONS } from '@/features/vendas'
import { VendasPorPeriodoChart } from '../components/VendasPorPeriodoChart'
import { ProdutosMaisVendidosTable } from '../components/ProdutosMaisVendidosTable'
import { GiroEstoqueTable } from '../components/GiroEstoqueTable'
import { useRelatorioVendas } from '../hooks/useRelatorioVendas'
import { useRelatorioProdutos } from '../hooks/useRelatorioProdutos'
import { useRelatorioGiroEstoque } from '../hooks/useRelatorioGiroEstoque'

function trintaDiasAtrasISO(): string {
  const data = new Date()
  data.setDate(data.getDate() - 30)
  return data.toISOString().slice(0, 10)
}

function hojeISO(): string {
  return new Date().toISOString().slice(0, 10)
}

// Painel de relatórios: vendas por período, top produtos e giro de estoque.
export function RelatoriosPage() {
  const [dataInicio, setDataInicio] = useState(trintaDiasAtrasISO())
  const [dataFim, setDataFim] = useState(hojeISO())
  const [origemCanal, setOrigemCanal] = useState('')

  const filtro = { data_inicio: dataInicio, data_fim: dataFim }
  // O filtro de canal vale só para "Faturamento por dia" (vendas-por-período).
  const vendasQuery = useRelatorioVendas({ ...filtro, origem_canal: origemCanal || undefined })
  const produtosQuery = useRelatorioProdutos(filtro)
  const giroQuery = useRelatorioGiroEstoque(filtro)

  return (
    <PageWrapper title="Relatórios" description="Vendas por período, produtos mais vendidos e giro de estoque.">
      <div className="mb-6 flex flex-wrap items-end gap-3">
        <div>
          <label htmlFor="relatorio-data-inicio" className="mb-1.5 block text-sm font-medium text-text">
            De
          </label>
          <Input id="relatorio-data-inicio" type="date" value={dataInicio} onChange={(event) => setDataInicio(event.target.value)} />
        </div>
        <div>
          <label htmlFor="relatorio-data-fim" className="mb-1.5 block text-sm font-medium text-text">
            Até
          </label>
          <Input id="relatorio-data-fim" type="date" value={dataFim} onChange={(event) => setDataFim(event.target.value)} />
        </div>
        <div className="w-56">
          <label htmlFor="relatorio-canal" className="mb-1.5 block text-sm font-medium text-text">
            Canal (faturamento por dia)
          </label>
          <Select id="relatorio-canal" value={origemCanal} onChange={(event) => setOrigemCanal(event.target.value)}>
            <option value="">Todos os canais</option>
            {ORIGEM_CANAL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </div>
      </div>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle>Faturamento por dia</CardTitle>
          </CardHeader>
          <VendasPorPeriodoChart vendas={vendasQuery.data?.data ?? []} isLoading={vendasQuery.isLoading} />
        </Card>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Produtos mais vendidos</CardTitle>
            </CardHeader>
            <ProdutosMaisVendidosTable produtos={produtosQuery.data?.data ?? []} isLoading={produtosQuery.isLoading} />
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Giro de estoque</CardTitle>
            </CardHeader>
            <GiroEstoqueTable itens={giroQuery.data?.data ?? []} isLoading={giroQuery.isLoading} />
          </Card>
        </div>
      </div>
    </PageWrapper>
  )
}
