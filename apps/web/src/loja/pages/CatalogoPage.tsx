import { useState } from 'react'
import { Search } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Skeleton } from '@/shared/components/ui/Skeleton'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { Pagination } from '@/shared/components/ui/Pagination'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { useCategoriasLoja, useProdutosLoja } from '../hooks/useLojaQueries'
import { ProdutoCard } from '../components/ProdutoCard'

const POR_PAGINA = 24

export function CatalogoPage() {
  const [categoriaId, setCategoriaId] = useState<string | undefined>(undefined)
  const [busca, setBusca] = useState('')
  const [page, setPage] = useState(1)
  const buscaAtrasada = useDebounce(busca.trim(), 300)

  const categorias = useCategoriasLoja()
  const produtos = useProdutosLoja({
    page,
    per_page: POR_PAGINA,
    categoria_id: categoriaId,
    q: buscaAtrasada || undefined,
  })

  function trocarCategoria(id: string | undefined) {
    setCategoriaId(id)
    setPage(1)
  }

  return (
    <div className="flex flex-col gap-6">
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
            onClick={() => trocarCategoria(undefined)}
          >
            Todas
          </Button>
          {categorias.data.map((categoria) => (
            <Button
              key={categoria.id}
              size="sm"
              variant={categoriaId === categoria.id ? 'primary' : 'outline'}
              aria-pressed={categoriaId === categoria.id}
              onClick={() => trocarCategoria(categoria.id)}
            >
              {categoria.nome}
            </Button>
          ))}
        </div>
      )}

      {produtos.isPending && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4" aria-busy="true">
          {Array.from({ length: 8 }).map((_, i) => (
            <Skeleton key={i} className="aspect-[3/4] w-full" />
          ))}
        </div>
      )}

      {produtos.data && produtos.data.data.length === 0 && (
        <EmptyState
          title="Nenhum produto encontrado"
          description="Tente outra busca ou escolha outra categoria."
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
  )
}
