import { Badge } from '@/shared/components/ui/Badge'
import { labelCanal } from '../lib/canal'

type Props = {
  canal: string
  className?: string
}

const canalTone: Record<string, 'neutral' | 'ok' | 'primary'> = {
  PDV: 'neutral',
  WHATSAPP: 'ok',
  NUVEMSHOP: 'primary',
}

// Badge do canal de origem do pedido (PDV / WhatsApp / Nuvemshop).
export function CanalBadge({ canal, className }: Props) {
  return (
    <Badge tone={canalTone[canal] ?? 'neutral'} className={className}>
      {labelCanal(canal)}
    </Badge>
  )
}
