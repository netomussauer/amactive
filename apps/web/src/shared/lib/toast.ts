import { useToastStore } from './toast-store'

// API imperativa para disparar toasts fora de componentes (ex: dentro de
// hooks de mutation/query). Para renderizar, ver shared/components/ui/Toaster.tsx.
export const toast = {
  success: (message: string) => useToastStore.getState().push('success', message),
  error: (message: string) => useToastStore.getState().push('error', message),
  info: (message: string) => useToastStore.getState().push('info', message),
}
