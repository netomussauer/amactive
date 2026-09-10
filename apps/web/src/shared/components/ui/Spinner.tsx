import { Loader2 } from 'lucide-react'
import { cn } from '@/shared/lib/utils'

export function Spinner({ className, label = 'Carregando…' }: { className?: string; label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-8 text-text-muted" role="status">
      <Loader2 className={cn('h-5 w-5 animate-spin', className)} aria-hidden="true" />
      <span>{label}</span>
    </div>
  )
}
