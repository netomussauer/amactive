import { describe, expect, it } from 'vitest'
import {
  CriarUsuarioSchema,
  AtualizarUsuarioFormSchema,
  RedefinirSenhaSchema,
  UsuarioDetalheResponseSchema,
} from './usuario.schema'

// Testes do schema Zod de usuário — cobre validação de nome/e-mail/senha e
// o enum de papel, espelhando docs/openapi.yaml CriarUsuarioRequest.
describe('CriarUsuarioSchema', () => {
  const usuarioValido = { nome: 'Ana Souza', email: 'ana@amactive.dev', senha: 'senha1234', papel: 'VENDEDOR' }

  it('aceita um payload válido', () => {
    const result = CriarUsuarioSchema.safeParse(usuarioValido)
    expect(result.success).toBe(true)
  })

  it('rejeita nome vazio', () => {
    const result = CriarUsuarioSchema.safeParse({ ...usuarioValido, nome: '' })
    expect(result.success).toBe(false)
  })

  it('rejeita e-mail inválido', () => {
    const result = CriarUsuarioSchema.safeParse({ ...usuarioValido, email: 'nao-e-email' })
    expect(result.success).toBe(false)
  })

  it('rejeita senha com menos de 8 caracteres', () => {
    const result = CriarUsuarioSchema.safeParse({ ...usuarioValido, senha: '1234567' })
    expect(result.success).toBe(false)
  })

  it('aceita senha com exatamente 8 caracteres', () => {
    const result = CriarUsuarioSchema.safeParse({ ...usuarioValido, senha: '12345678' })
    expect(result.success).toBe(true)
  })

  it('rejeita papel fora do enum', () => {
    const result = CriarUsuarioSchema.safeParse({ ...usuarioValido, papel: 'GERENTE' })
    expect(result.success).toBe(false)
  })

  it.each(['ADMIN', 'VENDEDOR', 'ESTOQUISTA'])('aceita o papel %s', (papel) => {
    const result = CriarUsuarioSchema.safeParse({ ...usuarioValido, papel })
    expect(result.success).toBe(true)
  })
})

describe('AtualizarUsuarioFormSchema', () => {
  it('aceita nome e papel válidos, sem e-mail/senha', () => {
    const result = AtualizarUsuarioFormSchema.safeParse({ nome: 'Ana Souza', papel: 'ADMIN' })
    expect(result.success).toBe(true)
  })

  it('rejeita nome com 1 caractere', () => {
    const result = AtualizarUsuarioFormSchema.safeParse({ nome: 'A', papel: 'ADMIN' })
    expect(result.success).toBe(false)
  })
})

describe('RedefinirSenhaSchema', () => {
  it('rejeita senha curta', () => {
    expect(RedefinirSenhaSchema.safeParse({ senha: '123' }).success).toBe(false)
  })

  it('aceita senha com 8+ caracteres', () => {
    expect(RedefinirSenhaSchema.safeParse({ senha: 'nova-senha-123' }).success).toBe(true)
  })
})

describe('UsuarioDetalheResponseSchema', () => {
  it('aceita uma resposta válida da API', () => {
    const result = UsuarioDetalheResponseSchema.safeParse({
      id: 'usuario-1',
      nome: 'Ana Souza',
      email: 'ana@amactive.dev',
      papel: 'ADMIN',
      ativo: true,
      criado_em: '2026-01-01T00:00:00Z',
    })
    expect(result.success).toBe(true)
  })

  it('nunca aceita/expõe um campo de senha (não faz parte do schema)', () => {
    const result = UsuarioDetalheResponseSchema.safeParse({
      id: 'usuario-1',
      nome: 'Ana Souza',
      email: 'ana@amactive.dev',
      papel: 'ADMIN',
      ativo: true,
      criado_em: '2026-01-01T00:00:00Z',
      senha_hash: 'nunca-deveria-vir-aqui',
    })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data).not.toHaveProperty('senha_hash')
    }
  })
})
