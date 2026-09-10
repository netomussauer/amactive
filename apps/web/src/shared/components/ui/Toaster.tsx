import { CheckCircle2, Info, XCircle, X } from 'lucide-react'
import { useToastStore } from '@/shared/lib/toast-store'
import { cn } from '@/shared/lib/utils'

const variantConfig = {
  success: { icon: CheckCircle2, className: 'border-status-ok text-status-ok' },
  error: { icon: XCircle, className: 'border-danger text-danger' },
  info: { icon: Info, className: 'border-primary text-primary' },
} as const

// Renderiza a fila global de toasts (shared/lib/toast-store.ts). Montado uma
// única vez em App.tsx.
export function Toaster() {
  const toasts = useToastStore((state) => state.toasts)
  const dismiss = useToastStore((state) => state.dismiss)

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex w-full max-w-sm flex-col gap-2">
      {toasts.map((item) => {
        const config = variantConfig[item.variant]
        const Icon = config.icon
        return (
          <div
            key={item.id}
            role="alert"
            className={cn(
              'flex items-start gap-2 rounded-lg border bg-bg p-3 text-sm shadow-md',
              config.className,
            )}
          >
            <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <p className="flex-1 text-text">{item.message}</p>
            <button
              type="button"
              aria-label="Fechar notificação"
              onClick={() => dismiss(item.id)}
              className="text-text-muted hover:text-text"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
