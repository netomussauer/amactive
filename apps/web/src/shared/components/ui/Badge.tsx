import type { HTMLAttributes } from 'react'
import { cn } from '@/shared/lib/utils'

type Tone = 'neutral' | 'ok' | 'baixo' | 'critico' | 'pendente' | 'confirmado' | 'cancelado' | 'primary'

type Props = HTMLAttributes<HTMLSpanElement> & {
  tone?: Tone
}

const toneClasses: Record<Tone, string> = {
  neutral: 'border-border text-text-muted',
  ok: 'border-status-ok text-status-ok',
  baixo: 'border-status-baixo text-status-baixo',
  critico: 'border-status-critico text-status-critico',
  pendente: 'border-status-pendente text-status-pendente',
  confirmado: 'border-status-confirmado text-status-confirmado',
  cancelado: 'border-status-cancelado text-status-cancelado',
  primary: 'border-primary text-primary',
}

export function Badge({ className, tone = 'neutral', children, ...props }: Props) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border bg-bg px-2.5 py-0.5 text-xs font-medium',
        toneClasses[tone],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  )
}
