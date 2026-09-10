import type { ReactNode } from 'react'
import { cn } from '@/shared/lib/utils'

type Props = {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}

// Container padrão de página: título + descrição + slot de ações (ex: botão
// "Novo produto") + conteúdo. Usado por todas as *Page.tsx das features.
export function PageWrapper({ title, description, actions, children, className }: Props) {
  return (
    <main className={cn('mx-auto w-full max-w-7xl px-4 py-6 md:px-6 md:py-8', className)}>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-sans text-2xl font-bold text-text">{title}</h1>
          {description && <p className="mt-1 text-sm text-text-muted">{description}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      {children}
    </main>
  )
}
