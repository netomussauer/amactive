import { describe, expect, it } from 'vitest'
import { CriarPedidoSchema, PagamentoRequestSchema } from './pedido.schema'

// Testes do schema Zod do pedido (contrato de POST /pedidos).
describe('CriarPedidoSchema', () => {
  const pedidoValido = {
    cliente_id: null,
    desconto: '0.00',
    itens: [{ variante_id: '11111111-1111-1111-1111-111111111111', quantidade: 2, desconto_item: '0.00' }],
    pagamentos: [{ forma_pagamento: 'DINHEIRO', valor: '100.00' }],
  }

  it('aceita um pedido válido com um item e um pagamento', () => {
    const result = CriarPedidoSchema.safeParse(pedidoValido)
    expect(result.success).toBe(true)
  })

  it('rejeita pedido sem itens', () => {
    const result = CriarPedidoSchema.safeParse({ ...pedidoValido, itens: [] })
    expect(result.success).toBe(false)
  })

  it('rejeita pedido sem formas de pagamento', () => {
    const result = CriarPedidoSchema.safeParse({ ...pedidoValido, pagamentos: [] })
    expect(result.success).toBe(false)
  })

  it('rejeita quantidade menor que 1', () => {
    const result = CriarPedidoSchema.safeParse({
      ...pedidoValido,
      itens: [{ variante_id: '11111111-1111-1111-1111-111111111111', quantidade: 0 }],
    })
    expect(result.success).toBe(false)
  })

  it('aceita cliente_id nulo (venda sem cliente vinculado)', () => {
    const result = CriarPedidoSchema.safeParse(pedidoValido)
    expect(result.success).toBe(true)
    if (result.success) expect(result.data.cliente_id).toBeNull()
  })
})

describe('PagamentoRequestSchema', () => {
  it('rejeita valor fora do formato decimal com 2 casas', () => {
    const result = PagamentoRequestSchema.safeParse({ forma_pagamento: 'PIX', valor: '100' })
    expect(result.success).toBe(false)
  })

  it('aceita valor no formato decimal correto', () => {
    const result = PagamentoRequestSchema.safeParse({ forma_pagamento: 'PIX', valor: '100.00' })
    expect(result.success).toBe(true)
  })

  it('rejeita forma de pagamento desconhecida', () => {
    const result = PagamentoRequestSchema.safeParse({ forma_pagamento: 'BOLETO', valor: '100.00' })
    expect(result.success).toBe(false)
  })
})
