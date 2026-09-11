import { Check } from 'lucide-react'
import { cn } from '@/shared/lib/utils'

export type StepperStep = {
  id: string
  label: string
}

type StepStatus = 'concluido' | 'atual' | 'pendente'

type Props = {
  steps: StepperStep[]
  currentStepId: string
  className?: string
}

const STATUS_LABEL: Record<StepStatus, string> = {
  concluido: 'Concluído',
  atual: 'Etapa atual',
  pendente: 'Pendente',
}

function getStatus(steps: StepperStep[], currentStepId: string, index: number): StepStatus {
  const currentIndex = steps.findIndex((step) => step.id === currentStepId)
  if (currentIndex === -1) return 'pendente'
  if (index < currentIndex) return 'concluido'
  if (index === currentIndex) return 'atual'
  return 'pendente'
}

// Indicador de progresso para fluxos multi-etapa (hoje: cadastro de produto —
// dados → variantes → imagens). Puramente indicativo: não é clicável/navegável,
// já que as etapas podem viver em telas diferentes (ex: "Imagens" acontece em
// ProdutoDetalhePage, não no mesmo fluxo de ProdutoNovoPage). Pensado para 2-3
// steps nomeados; não generalizar para casos que precisem de navegação por
// clique ou etapas dinâmicas sem necessidade real.
export function Stepper({ steps, currentStepId, className }: Props) {
  return (
    <ol aria-label="Etapas do cadastro" className={cn('flex flex-wrap items-start', className)}>
      {steps.map((step, index) => {
        const status = getStatus(steps, currentStepId, index)
        const isLast = index === steps.length - 1
        return (
          <li
            key={step.id}
            aria-current={status === 'atual' ? 'step' : undefined}
            className={cn('flex items-center', !isLast && 'flex-1')}
          >
            <div className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={cn(
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-xs font-semibold',
                  status === 'concluido' && 'border-primary bg-primary text-white',
                  status === 'atual' && 'border-primary bg-primary-subtle text-primary',
                  status === 'pendente' && 'border-border bg-bg text-text-muted',
                )}
              >
                {status === 'concluido' ? <Check className="h-4 w-4" aria-hidden="true" /> : index + 1}
              </span>
              <span
                className={cn(
                  'whitespace-nowrap text-sm font-medium',
                  status === 'atual' ? 'text-text' : 'text-text-muted',
                )}
              >
                {step.label}
                <span className="sr-only"> ({STATUS_LABEL[status]})</span>
              </span>
            </div>
            {!isLast && (
              <span
                aria-hidden="true"
                className={cn('mx-3 h-px min-w-[24px] flex-1', status === 'concluido' ? 'bg-primary' : 'bg-border')}
              />
            )}
          </li>
        )
      })}
    </ol>
  )
}
