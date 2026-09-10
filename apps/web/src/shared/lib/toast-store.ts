import { create } from 'zustand'

export type ToastVariant = 'success' | 'error' | 'info'

export type ToastItem = {
  id: string
  variant: ToastVariant
  message: string
}

type ToastState = {
  toasts: ToastItem[]
  push: (variant: ToastVariant, message: string) => void
  dismiss: (id: string) => void
}

// Estado global de toasts (feedback de erro/sucesso). Ver
// docs/frontend-architecture.md — tratamento de erro global do item 1 do escopo.
export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (variant, message) =>
    set((state) => ({
      toasts: [...state.toasts, { id: crypto.randomUUID(), variant, message }],
    })),
  dismiss: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}))
