import type { ReactNode } from 'react'
import { cn } from '@/shared/lib/utils'

type Props = {
  title: string
  description?: string
  action?: ReactNode
  icon?: ReactNode
  className?: string
}

export function EmptyState({ title, description, action, icon, className }: Props) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border p-12 text-center', className)}>
      {icon && <div className="text-text-muted">{icon}</div>}
      <div>
        <p className="font-sans text-base font-semibold text-text">{title}</p>
        {description && <p className="mt-1 text-sm text-text-muted">{description}</p>}
      </div>
      {action}
    </div>
  )
}
