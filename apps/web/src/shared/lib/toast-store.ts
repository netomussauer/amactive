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

// `crypto.randomUUID()` só existe em contexto seguro (HTTPS ou localhost —
// https://developer.mozilla.org/docs/Web/API/Crypto/randomUUID): em
// qualquer acesso via IP/hostname puro HTTP do laboratório (ex:
// http://192.168.1.213, http://app.amactive.local) ele é `undefined`, e
// chamar isso levanta `TypeError: crypto.randomUUID is not a function`
// dentro do próprio push() do toast (bug real, 2026-10-07). Como esse push
// é chamado de dentro do onSuccess/onError global do MutationCache (ver
// shared/lib/query-client.ts), a exceção não fica isolada no toast: ela
// propaga pelo try/catch do TanStack Query e faz a mutation inteira ser
// tratada como erro — inclusive abortando o onSuccess passado por chamada
// a mutate() (ex: a navegação pro passo 2 em ProdutoNovoPage), mesmo
// quando a escrita no backend já tinha sido concluída com sucesso. Um id
// de toast só precisa ser único dentro da lista local, não
// criptograficamente forte, então não há motivo pra depender da Web
// Crypto API aqui.
function gerarIdToast(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

// Tempo até o toast sumir sozinho (bug real, 2026-10-10: nunca existiu
// auto-dismiss aqui — `dismiss()` só era chamado pelo clique manual no X do
// Toaster, então toasts ficavam empilhados na tela indefinidamente até o
// usuário fechar um por um). Erro fica mais tempo (mensagem costuma ser mais
// importante de ler) do que sucesso/info.
const DURACAO_MS: Record<ToastVariant, number> = {
  success: 4000,
  info: 4000,
  error: 6000,
}

// Estado global de toasts (feedback de erro/sucesso). Ver
// docs/frontend-architecture.md — tratamento de erro global do item 1 do escopo.
export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  push: (variant, message) => {
    const id = gerarIdToast()
    set((state) => ({ toasts: [...state.toasts, { id, variant, message }] }))
    // Se o usuário já fechou manualmente antes do timer disparar, dismiss()
    // com esse id vira um no-op (filter não acha nada pra remover).
    setTimeout(() => useToastStore.getState().dismiss(id), DURACAO_MS[variant])
  },
  dismiss: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}))
