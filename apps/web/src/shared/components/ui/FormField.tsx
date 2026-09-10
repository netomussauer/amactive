import type { ReactNode } from 'react'
import { Label } from './Label'

type Props = {
  label: string
  htmlFor: string
  required?: boolean
  error?: string
  hint?: string
  children: ReactNode
}

// Wrapper de campo de formulário: label + controle + mensagem de erro
// acessível (role="alert" + aria-describedby amarrado pelo caller no input).
export function FormField({ label, htmlFor, required, error, hint, children }: Props) {
  const errorId = `${htmlFor}-error`
  return (
    <div>
      <Label htmlFor={htmlFor} required={required}>
        {label}
      </Label>
      {children}
      {hint && !error && <p className="mt-1 text-xs text-text-muted">{hint}</p>}
      {error && (
        <p id={errorId} role="alert" className="mt-1 text-xs text-danger">
          {error}
        </p>
      )}
    </div>
  )
}
