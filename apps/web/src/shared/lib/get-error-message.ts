import { ZodError } from 'zod'
import { ApiError } from './api-client'

// Traduz qualquer erro capturado (ApiError da API, erro de rede, etc.) em uma
// mensagem amigável para exibir em toasts/mensagens inline.
export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    // 403 (AcessoNegado) — o backend aplica RBAC por papel em todo endpoint
    // (ver docs/openapi.yaml, x-roles). Toda ação de escrita fora do papel
    // do usuário já deveria estar oculta na UI (ver shared/lib/permissoes.ts
    // e shared/hooks/usePermissoes.ts); isto aqui é a rede de segurança para
    // qualquer caso que a UI ainda não cubra — sempre uma mensagem amigável,
    // independente do texto exato vindo da API.
    if (error.status === 403) {
      return error.detail || 'Você não tem permissão para realizar esta ação.'
    }
    return error.detail || error.title || 'Ocorreu um erro inesperado.'
  }
  // ZodError.message é o JSON.stringify() bruto do array de issues (ver
  // zod/src/ZodError.ts) — sem este caso cai no `error instanceof Error`
  // abaixo e mostra esse JSON cru para o usuário (bug real, 2026-09-28:
  // aconteceu quando um schema de resposta divergiu do formato real da API).
  // Um ZodError chegando até aqui sempre indica um schema desalinhado, não
  // algo que o usuário possa corrigir — nunca é acionável mostrar os
  // detalhes técnicos.
  if (error instanceof ZodError) {
    return 'Ocorreu um erro inesperado ao processar a resposta do servidor.'
  }
  if (error instanceof Error) {
    if (error.message === 'Failed to fetch') {
      return 'Não foi possível conectar ao servidor. Verifique sua conexão.'
    }
    return error.message
  }
  return 'Ocorreu um erro inesperado.'
}
