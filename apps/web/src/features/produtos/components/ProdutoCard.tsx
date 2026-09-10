import { Card } from '@/shared/components/ui/Card'
import { Badge } from '@/shared/components/ui/Badge'
import type { Produto } from '../types/produto.types'

type Props = {
  produto: Produto
}

export function ProdutoCard({ produto }: Props) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="font-sans text-xl font-semibold text-text">{produto.nome}</h2>
          <p className="mt-1 text-sm text-text-muted">{produto.marca}</p>
          {produto.descricao && <p className="mt-2 text-sm text-text">{produto.descricao}</p>}
        </div>
        <Badge tone={produto.ativo ? 'ok' : 'neutral'}>{produto.ativo ? 'Ativo' : 'Inativo'}</Badge>
      </div>
    </Card>
  )
}
