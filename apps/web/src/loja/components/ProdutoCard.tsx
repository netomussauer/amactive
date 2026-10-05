import { Link } from 'react-router-dom'
import { Badge } from '@/shared/components/ui/Badge'
import { formatCurrencyBRL, formatPercent } from '@/shared/lib/format'
import type { ProdutoResumoLoja } from '../schemas/loja.schema'

type Props = { produto: ProdutoResumoLoja }

export function ProdutoCard({ produto }: Props) {
  const comDesconto = produto.desconto_percentual !== null

  return (
    <Link
      to={`/produtos/${produto.id}`}
      className="group flex flex-col overflow-hidden rounded-lg border border-border bg-bg transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <div className="relative aspect-[3/4] bg-bg-subtle">
        {produto.imagem_principal_url ? (
          <img
            src={produto.imagem_principal_url}
            alt={produto.nome}
            loading="lazy"
            className="h-full w-full object-cover transition-transform group-hover:scale-[1.02]"
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-text-muted">
            Sem imagem
          </div>
        )}
        {comDesconto && (
          <div className="absolute left-2 top-2">
            <Badge tone="primary">-{formatPercent(produto.desconto_percentual)}</Badge>
          </div>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-1 p-3">
        <p className="line-clamp-2 text-sm font-medium text-text">{produto.nome}</p>
        {produto.cores.length > 0 && (
          <p className="text-xs text-text-muted">
            {produto.cores.length} {produto.cores.length === 1 ? 'cor' : 'cores'}
          </p>
        )}
        <p className="mt-auto pt-1 text-sm">
          <span className="text-text-muted">a partir de </span>
          <span className="font-semibold text-primary">
            {formatCurrencyBRL(produto.preco_a_partir_de)}
          </span>
        </p>
      </div>
    </Link>
  )
}
