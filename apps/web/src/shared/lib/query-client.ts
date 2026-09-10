import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query'
import { ApiError } from './api-client'
import { getErrorMessage } from './get-error-message'
import { toast } from './toast'

// Config global do TanStack Query. Ver docs/frontend-architecture.md §5.4
// (staleTime por tipo de dado é sobrescrito em cada hook de feature).
//
// Tratamento de erro global: falhas de query (listagens/detalhes) e de
// mutation sem onError próprio caem aqui e viram um toast — hooks que
// precisam de tratamento específico (ex: 422 de estoque insuficiente no PDV)
// continuam livres para adicionar seu próprio onError, que roda em conjunto.
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
        return failureCount < 1
      },
    },
  },
  queryCache: new QueryCache({
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) return // tratado pelo AuthGuard
      toast.error(getErrorMessage(error))
    },
  }),
  mutationCache: new MutationCache({
    onError: (error) => {
      if (error instanceof ApiError && error.status === 401) return
      toast.error(getErrorMessage(error))
    },
  }),
})
