import { describe, expect, it } from 'vitest'
import { getPermissoes, primeiraRotaPermitida } from './permissoes'
import { routes } from './routes'
import { PapelUsuario } from '@/shared/types/api.types'
import type { Permissoes } from './permissoes'

// Matriz de RBAC esperada por papel — espelha docs/openapi.yaml
// (info.description + x-roles). Qualquer alteração aqui precisa vir
// acompanhada da mudança correspondente no backend (e vice-versa).
const MATRIZ_ESPERADA: Record<PapelUsuario, Permissoes> = {
  ADMIN: {
    podeGerenciarCatalogo: true,
    podeRegistrarMovimentacaoEstoque: true,
    podeVenderNoPdv: true,
    podeGerenciarClientes: true,
    podeGerenciarFornecedores: true,
    podeVerRelatorios: true,
    podeGerenciarUsuarios: true,
  },
  VENDEDOR: {
    podeGerenciarCatalogo: false,
    podeRegistrarMovimentacaoEstoque: false,
    podeVenderNoPdv: true,
    podeGerenciarClientes: true,
    podeGerenciarFornecedores: false,
    podeVerRelatorios: false,
    podeGerenciarUsuarios: false,
  },
  ESTOQUISTA: {
    podeGerenciarCatalogo: true,
    podeRegistrarMovimentacaoEstoque: true,
    podeVenderNoPdv: false,
    podeGerenciarClientes: false,
    podeGerenciarFornecedores: true,
    podeVerRelatorios: false,
    podeGerenciarUsuarios: false,
  },
}

describe('getPermissoes', () => {
  it.each(Object.entries(MATRIZ_ESPERADA))('resolve corretamente cada flag para o papel %s', (papel, esperado) => {
    const permissoes = getPermissoes(papel as PapelUsuario)

    for (const [flag, valorEsperado] of Object.entries(esperado) as Array<[keyof Permissoes, boolean]>) {
      expect(permissoes[flag], `${papel}.${flag}`).toBe(valorEsperado)
    }
  })

  it('retorna nenhuma permissão quando o papel é null', () => {
    const permissoes = getPermissoes(null)
    expect(Object.values(permissoes).every((flag) => flag === false)).toBe(true)
  })

  it('retorna nenhuma permissão quando o papel é undefined (usuário ainda não carregado)', () => {
    const permissoes = getPermissoes(undefined)
    expect(Object.values(permissoes).every((flag) => flag === false)).toBe(true)
  })
})

describe('primeiraRotaPermitida', () => {
  it('ADMIN vai para o dashboard', () => {
    expect(primeiraRotaPermitida('ADMIN')).toBe(routes.dashboard)
  })

  it('VENDEDOR vai para o PDV', () => {
    expect(primeiraRotaPermitida('VENDEDOR')).toBe(routes.pdv)
  })

  it('ESTOQUISTA vai para Produtos', () => {
    expect(primeiraRotaPermitida('ESTOQUISTA')).toBe(routes.produtos)
  })

  it('sem papel (deslogado) cai no destino seguro (Produtos)', () => {
    expect(primeiraRotaPermitida(null)).toBe(routes.produtos)
  })
})
