import { Link } from 'react-router-dom'
import { Badge } from '@/shared/components/ui/Badge'
import { getMediaUrl } from '@/shared/lib/api-client'
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
      {/* min-h-0 min-w-0: sem isso, uma foto cuja proporção natural é mais
          alta que 3:4 "vaza" através do mínimo implícito (min-height:auto)
          de um item flex com conteúdo substituído (<img>), e a caixa cresce
          para a proporção da FOTO em vez de respeitar aspect-[3/4] — o card
          "Sem imagem" (sem <img>) sempre ficava correto, só os com foto real
          variavam de altura entre si (bug real, 2026-10-09; reproduzido e
          confirmado isoladamente antes do fix: com min-h-0/min-w-0, uma
          imagem 855×1280 e um card sem imagem medem exatamente a mesma
          altura; sem, a imagem "vazava" sua proporção natural). */}
      <div className="relative aspect-[3/4] min-h-0 min-w-0 bg-bg-subtle">
        {produto.imagem_principal_url ? (
          <img
            src={getMediaUrl(produto.imagem_principal_url)}
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
