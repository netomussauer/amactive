import { describe, expect, it } from 'vitest'
import { getErrorMessage } from './get-error-message'
import { ApiError } from './api-client'

describe('getErrorMessage', () => {
  it('usa o detail da API quando presente', () => {
    const error = new ApiError('erro-generico', 422, 'Estoque insuficiente para este SKU.')
    expect(getErrorMessage(error)).toBe('Estoque insuficiente para este SKU.')
  })

  it('cai para o title quando não há detail', () => {
    const error = new ApiError('Erro de validação', 422)
    expect(getErrorMessage(error)).toBe('Erro de validação')
  })

  it('403 sem detail retorna mensagem amigável de acesso negado', () => {
    const error = new ApiError('acesso-negado', 403)
    expect(getErrorMessage(error)).toBe('Você não tem permissão para realizar esta ação.')
  })

  it('403 com detail da API preserva a mensagem específica do backend', () => {
    const error = new ApiError('acesso-negado', 403, 'Seu papel (VENDEDOR) não pode registrar movimentações de estoque.')
    expect(getErrorMessage(error)).toBe('Seu papel (VENDEDOR) não pode registrar movimentações de estoque.')
  })

  it('trata "Failed to fetch" como erro de conexão', () => {
    const error = new Error('Failed to fetch')
    expect(getErrorMessage(error)).toBe('Não foi possível conectar ao servidor. Verifique sua conexão.')
  })

  it('usa a mensagem de um Error genérico', () => {
    expect(getErrorMessage(new Error('algo quebrou'))).toBe('algo quebrou')
  })

  it('tem um fallback para valores desconhecidos', () => {
    expect(getErrorMessage('string qualquer')).toBe('Ocorreu um erro inesperado.')
  })
})
