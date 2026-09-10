import { ApiError } from './api-client'

// Traduz qualquer erro capturado (ApiError da API, erro de rede, etc.) em uma
// mensagem amigável para exibir em toasts/mensagens inline.
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.detail || error.title || 'Ocorreu um erro inesperado.'
  }
  if (error instanceof Error) {
    if (error.message === 'Failed to fetch') {
      return 'Não foi possível conectar ao servidor. Verifique sua conexão.'
    }
    return error.message
  }
  return 'Ocorreu um erro inesperado.'
}
