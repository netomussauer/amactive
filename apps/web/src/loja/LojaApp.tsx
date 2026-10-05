import { useEffect } from 'react'
import { QueryClientProvider } from '@tanstack/react-query'
import { RouterProvider } from 'react-router-dom'
import { queryClient } from '@/shared/lib/query-client'
import { Toaster } from '@/shared/components/ui/Toaster'
import { lojaRouter } from './router'

// Raiz da vitrine pública. Compartilha o QueryClient e o Toaster do sistema,
// mas não o router, a sessão nem os guards administrativos.
export default function LojaApp() {
  useEffect(() => {
    document.title = 'AMACTIVE — Loja online'
  }, [])

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={lojaRouter} />
      <Toaster />
    </QueryClientProvider>
  )
}
