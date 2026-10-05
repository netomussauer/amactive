import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, X } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Select } from '@/shared/components/ui/Select'
import { Skeleton } from '@/shared/components/ui/Skeleton'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { Pagination } from '@/shared/components/ui/Pagination'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { useCategoriasLoja, useOpcoesFiltroLoja, useProdutosLoja } from '../hooks/useLojaQueries'
import { ProdutoCard } from '../components/ProdutoCard'
import { HeroBanner } from '../components/HeroBanner'
import { ComoFunciona } from '../components/ComoFunciona'
import { FAIXAS_PRECO, ORDENACOES, faixaPorId, ordemValida } from '../lib/filtros'

const POR_PAGINA = 24

export function CatalogoPage() {
  // Filtros na URL: compartilháveis e com "voltar" do navegador funcionando.
  const [params, setParams] = useSearchParams()
  const categoriaId = params.get('categoria') ?? undefined
  const cor = params.get('cor') ?? undefined
  const tamanho = params.get('tamanho') ?? undefined
  const faixa = faixaPorId(params.get('preco'))
  const ordem = ordemValida(params.get('ordem'))

  const [busca, setBusca] = useState('')
  const [page, setPage] = useState(1)
  const buscaAtrasada = useDebounce(busca.trim(), 300)

  const categorias = useCategoriasLoja()
  const opcoes = useOpcoesFiltroLoja()
  const produtos = useProdutosLoja({
    page,
    per_page: POR_PAGINA,
    categoria_id: categoriaId,
    q: buscaAtrasada || undefined,
    cor,
    tamanho,
    preco_min: faixa.min,
    preco_max: faixa.max,
    ordem,
  })

  const semFiltros = !categoriaId && !cor && !tamanho && faixa.id === 'todas' && !buscaAtrasada
  // Destaques: as peças com maior desconto. Só aparece na vitrine sem filtros.
  const destaques = useProdutosLoja({ page: 1, per_page: 4, ordem: 'desconto' })

  const filtrosAtivos = !semFiltros || ordem !== 'nome'

  function definir(chave: string, valor: string | undefined) {
    setParams(
      (anterior) => {
        const proximo = new URLSearchParams(anterior)
        if (valor) proximo.set(chave, valor)
        else proximo.delete(chave)
        return proximo
      },
      { replace: true },
    )
    setPage(1)
  }

  function limparFiltros() {
    setBusca('')
    setParams({}, { replace: true })
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-8">
      <HeroBanner />

      {semFiltros && destaques.data && destaques.data.data.length > 0 && (
        <section aria-labelledby="destaques-titulo" className="flex flex-col gap-4">
          <h2 id="destaques-titulo" className="font-sans text-xl font-semibold text-text">
            Em destaque
          </h2>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {destaques.data.data.map((produto) => (
              <ProdutoCard key={produto.id} produto={produto} />
            ))}
          </div>
        </section>
      )}

      <div id="colecao" className="flex scroll-mt-20 flex-col gap-4">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <h1 className="font-sans text-2xl font-semibold text-text">Coleção</h1>
          <div className="relative w-full sm:w-72">
            <Search
              className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted"
              aria-hidden="true"
            />
            <Input
              type="search"
              aria-label="Buscar produto"
              placeholder="Buscar produto"
              className="pl-9"
              value={busca}
              onChange={(e) => {
                setBusca(e.target.value)
                setPage(1)
              }}
            />
          </div>
        </div>

        {categorias.data && categorias.data.length > 0 && (
          <div className="flex flex-wrap gap-2" role="group" aria-label="Filtrar por categoria">
            <Button
              size="sm"
              variant={categoriaId === undefined ? 'primary' : 'outline'}
              aria-pressed={categoriaId === undefined}
              onClick={() => definir('categoria', undefined)}
            >
              Todas
            </Button>
            {categorias.data.map((categoria) => (
              <Button
                key={categoria.id}
                size="sm"
                variant={categoriaId === categoria.id ? 'primary' : 'outline'}
                aria-pressed={categoriaId === categoria.id}
                onClick={() => definir('categoria', categoria.id)}
              >
                {categoria.nome}
              </Button>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4" role="group" aria-label="Filtros e ordenação">
          <FiltroSelect
            id="filtro-cor"
            label="Cor"
            valor={cor ?? ''}
            onChange={(v) => definir('cor', v || undefined)}
            opcoes={[{ value: '', label: 'Todas as cores' }, ...(opcoes.data?.cores ?? []).map((c) => ({ value: c, label: c }))]}
          />
          <FiltroSelect
            id="filtro-tamanho"
            label="Tamanho"
            valor={tamanho ?? ''}
            onChange={(v) => definir('tamanho', v || undefined)}
            opcoes={[{ value: '', label: 'Todos os tamanhos' }, ...(opcoes.data?.tamanhos ?? []).map((t) => ({ value: t, label: t }))]}
          />
          <FiltroSelect
            id="filtro-preco"
            label="Preço"
            valor={faixa.id === 'todas' ? '' : faixa.id}
            onChange={(v) => definir('preco', v || undefined)}
            opcoes={FAIXAS_PRECO.map((f) => ({ value: f.id === 'todas' ? '' : f.id, label: f.label }))}
          />
          <FiltroSelect
            id="filtro-ordem"
            label="Ordenar por"
            valor={ordem}
            onChange={(v) => definir('ordem', v === 'nome' ? undefined : v)}
            opcoes={ORDENACOES.map((o) => ({ value: o.value, label: o.label }))}
          />
        </div>

        <div className="flex items-center justify-between text-sm text-text-muted">
          <p aria-live="polite">
            {produtos.data ? `${produtos.data.pagination.total} produto(s)` : 'Carregando…'}
          </p>
          {filtrosAtivos && (
            <Button variant="ghost" size="sm" onClick={limparFiltros}>
              <X className="h-4 w-4" aria-hidden="true" />
              Limpar filtros
            </Button>
          )}
        </div>

        {produtos.isPending && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4" aria-busy="true">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="aspect-[3/4] w-full" />
            ))}
          </div>
        )}

        {produtos.data && produtos.data.data.length === 0 && (
          <EmptyState
            title="Nenhum produto com esses filtros"
            description="Tente outra cor, tamanho ou faixa de preço."
            action={
              <Button variant="outline" size="sm" onClick={limparFiltros}>
                Limpar filtros
              </Button>
            }
          />
        )}

        {produtos.data && produtos.data.data.length > 0 && (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
              {produtos.data.data.map((produto) => (
                <ProdutoCard key={produto.id} produto={produto} />
              ))}
            </div>
            <Pagination pagination={produtos.data.pagination} onPageChange={setPage} />
          </>
        )}
      </div>

      <ComoFunciona />
    </div>
  )
}

type OpcaoFiltro = { value: string; label: string }

function FiltroSelect({
  id,
  label,
  valor,
  onChange,
  opcoes,
}: {
  id: string
  label: string
  valor: string
  onChange: (valor: string) => void
  opcoes: OpcaoFiltro[]
}) {
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-medium text-text-muted">
        {label}
      </label>
      <Select id={id} value={valor} onChange={(e) => onChange(e.target.value)}>
        {opcoes.map((opcao) => (
          <option key={`${opcao.value}-${opcao.label}`} value={opcao.value}>
            {opcao.label}
          </option>
        ))}
      </Select>
    </div>
  )
}
