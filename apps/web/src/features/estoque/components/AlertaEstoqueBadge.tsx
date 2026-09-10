import { Badge } from '@/shared/components/ui/Badge'

type Props = {
  quantidade: number
  emAlerta: boolean
}

// Ver docs/frontend-architecture.md §7 — tokens de status de estoque (ok/baixo/crítico).
export function AlertaEstoqueBadge({ quantidade, emAlerta }: Props) {
  if (!emAlerta) return <Badge tone="ok">Estoque ok</Badge>
  if (quantidade <= 0) return <Badge tone="critico">Sem estoque</Badge>
  return <Badge tone="baixo">Estoque baixo</Badge>
}
