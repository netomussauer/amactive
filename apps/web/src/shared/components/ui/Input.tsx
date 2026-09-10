import { forwardRef } from 'react'
import type { InputHTMLAttributes } from 'react'
import { cn } from '@/shared/lib/utils'

type Props = InputHTMLAttributes<HTMLInputElement> & {
  invalid?: boolean
}

export const Input = forwardRef<HTMLInputElement, Props>(
  ({ className, invalid, ...props }, ref) => {
    return (
      <input
        ref={ref}
        aria-invalid={invalid}
        className={cn(
          'h-10 w-full rounded-md border border-border bg-bg px-3 text-sm text-text placeholder:text-text-muted',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary',
          'disabled:cursor-not-allowed disabled:opacity-50',
          invalid && 'border-danger focus-visible:ring-danger',
          className,
        )}
        {...props}
      />
    )
  },
)
Input.displayName = 'Input'
