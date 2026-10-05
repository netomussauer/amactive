import { describe, expect, it } from 'vitest'
import { faixaPorId, ordemValida } from './filtros'

describe('faixaPorId', () => {
  it('traduz a faixa da URL nos limites enviados à API', () => {
    const ate100 = faixaPorId('ate-100')
    expect(ate100.max).toBe('100.00')
    expect(ate100.min).toBeUndefined()

    const entre = faixaPorId('100-150')
    expect(entre.min).toBe('100.00')
    expect(entre.max).toBe('150.00')

    const acima = faixaPorId('acima-150')
    expect(acima.min).toBe('150.00')
    expect(acima.max).toBeUndefined()
  })

  it('valor desconhecido ou ausente cai em "todos os preços"', () => {
    expect(faixaPorId(null).id).toBe('todas')
    expect(faixaPorId('qualquer-coisa').id).toBe('todas')
  })
})

describe('ordemValida', () => {
  it('aceita as ordenações conhecidas', () => {
    expect(ordemValida('preco_asc')).toBe('preco_asc')
    expect(ordemValida('desconto')).toBe('desconto')
  })

  it('ordenação desconhecida ou ausente cai em nome', () => {
    expect(ordemValida(null)).toBe('nome')
    expect(ordemValida('aleatoria')).toBe('nome')
  })
})
