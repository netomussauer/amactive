import { describe, expect, it } from 'vitest'
import { calcularDescontoItem } from './calcular-desconto-item'

// Testes do cálculo de desconto_item enviado em POST /pedidos — o frontend
// calcula esse valor a partir do preco_promocional já pronto da API (nunca
// recalcula o percentual em si, ver docs/openapi.yaml VarianteResponse).
describe('calcularDescontoItem', () => {
  it('retorna "0.00" quando não há preço promocional', () => {
    expect(calcularDescontoItem('100.00', null, 3)).toBe('0.00')
    expect(calcularDescontoItem('100.00', undefined, 3)).toBe('0.00')
  })

  it('calcula o desconto multiplicando a diferença unitária pela quantidade', () => {
    expect(calcularDescontoItem('100.00', '85.00', 1)).toBe('15.00')
    expect(calcularDescontoItem('100.00', '85.00', 3)).toBe('45.00')
  })

  it('arredonda para 2 casas decimais', () => {
    expect(calcularDescontoItem('129.90', '110.42', 2)).toBe('38.96')
  })

  it('retorna "0.00" quando o preço promocional não é menor que o preço original', () => {
    expect(calcularDescontoItem('100.00', '100.00', 2)).toBe('0.00')
    expect(calcularDescontoItem('100.00', '120.00', 2)).toBe('0.00')
  })
})
