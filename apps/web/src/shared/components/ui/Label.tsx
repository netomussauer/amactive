import type { LabelHTMLAttributes } from 'react'
import { cn } from '@/shared/lib/utils'

type Props = LabelHTMLAttributes<HTMLLabelElement> & {
  required?: boolean
}

export function Label({ className, required, children, ...props }: Props) {
  return (
    <label className={cn('mb-1.5 block text-sm font-medium text-text', className)} {...props}>
      {children}
      {required && (
        <span className="ml-0.5 text-danger" aria-hidden="true">
          *
        </span>
      )}
    </label>
  )
}
