import { afterEach, describe, expect, it } from 'vitest'
import { renderHook } from '@testing-library/react'
import { usePermissoes } from './usePermissoes'
import { useAuth } from './useAuth'

describe('usePermissoes', () => {
  afterEach(() => {
    useAuth.setState({ user: null, isAuthenticated: false })
  })

  it('deriva as permissões do papel do usuário logado', () => {
    useAuth.setState({
      user: { id: '1', nome: 'Vendedora', email: 'vendedora@amactive.dev', papel: 'VENDEDOR' },
      isAuthenticated: true,
    })

    const { result } = renderHook(() => usePermissoes())

    expect(result.current.podeVenderNoPdv).toBe(true)
    expect(result.current.podeGerenciarCatalogo).toBe(false)
    expect(result.current.podeGerenciarFornecedores).toBe(false)
  })

  it('não concede nenhuma permissão quando não há usuário logado', () => {
    const { result } = renderHook(() => usePermissoes())

    expect(Object.values(result.current).every((flag) => flag === false)).toBe(true)
  })
})
