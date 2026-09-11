import { describe, expect, it } from 'vitest'
import { CriarProdutoSchema, ProdutoResponseSchema, VarianteResponseSchema } from './produto.schema'

// Testes do schema Zod de produto — cobre a regra de desconto_percentual
// (0 < x <= 100, null = sem promoção) espelhada de docs/openapi.yaml.
describe('CriarProdutoSchema — desconto_percentual', () => {
  const produtoValido = { nome: 'Legging Fitness', marca: 'AMACTIVE' }

  it('aceita produto sem desconto_percentual (campo opcional)', () => {
    const result = CriarProdutoSchema.safeParse(produtoValido)
    expect(result.success).toBe(true)
  })

  it('aceita desconto_percentual nulo (sem promoção ativa)', () => {
    const result = CriarProdutoSchema.safeParse({ ...produtoValido, desconto_percentual: null })
    expect(result.success).toBe(true)
    if (result.success) expect(result.data.desconto_percentual).toBeNull()
  })

  it('aceita um percentual válido entre 0 (exclusivo) e 100', () => {
    const result = CriarProdutoSchema.safeParse({ ...produtoValido, desconto_percentual: 15 })
    expect(result.success).toBe(true)
    if (result.success) expect(result.data.desconto_percentual).toBe(15)
  })

  it('aceita exatamente 100', () => {
    const result = CriarProdutoSchema.safeParse({ ...produtoValido, desconto_percentual: 100 })
    expect(result.success).toBe(true)
  })

  it('rejeita 0 (deve ser maior que 0)', () => {
    const result = CriarProdutoSchema.safeParse({ ...produtoValido, desconto_percentual: 0 })
    expect(result.success).toBe(false)
  })

  it('rejeita valor negativo', () => {
    const result = CriarProdutoSchema.safeParse({ ...produtoValido, desconto_percentual: -5 })
    expect(result.success).toBe(false)
  })

  it('rejeita valor acima de 100', () => {
    const result = CriarProdutoSchema.safeParse({ ...produtoValido, desconto_percentual: 100.5 })
    expect(result.success).toBe(false)
  })
})

describe('ProdutoResponseSchema — desconto_percentual', () => {
  const produtoBase = {
    id: 'produto-1',
    nome: 'Legging Fitness',
    marca: 'AMACTIVE',
    ativo: true,
    criado_em: '2026-01-01T00:00:00Z',
  }

  it('aceita resposta com desconto_percentual nulo', () => {
    const result = ProdutoResponseSchema.safeParse({ ...produtoBase, desconto_percentual: null })
    expect(result.success).toBe(true)
  })

  it('aceita resposta com desconto_percentual numérico', () => {
    const result = ProdutoResponseSchema.safeParse({ ...produtoBase, desconto_percentual: 20 })
    expect(result.success).toBe(true)
  })
})

describe('VarianteResponseSchema — preco_promocional', () => {
  const varianteBase = {
    id: 'variante-1',
    produto_id: 'produto-1',
    sku: 'LEG-CORAL-M',
    tamanho: 'M',
    cor: 'Coral',
    preco_venda: '100.00',
    ativo: true,
    quantidade_estoque: 10,
  }

  it('aceita variante sem promoção (campos nulos)', () => {
    const result = VarianteResponseSchema.safeParse({
      ...varianteBase,
      desconto_percentual: null,
      preco_promocional: null,
    })
    expect(result.success).toBe(true)
  })

  it('aceita variante com preco_promocional já calculado pela API', () => {
    const result = VarianteResponseSchema.safeParse({
      ...varianteBase,
      desconto_percentual: '15.00',
      preco_promocional: '85.00',
    })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.preco_promocional).toBe('85.00')
      expect(result.data.desconto_percentual).toBe('15.00')
    }
  })
})
