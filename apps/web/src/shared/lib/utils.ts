import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

// Utilitário padrão para mesclar classes Tailwind condicionalmente.
// Ver docs/frontend-architecture.md — nunca usar template strings para className.
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}
