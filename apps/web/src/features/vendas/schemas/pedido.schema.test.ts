import { describe, expect, it } from 'vitest'
import {
  CriarPedidoSchema,
  PagamentoRequestSchema,
  PedidoDetalheResponseSchema,
  PedidoListResponseSchema,
} from './pedido.schema'

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

  it('aceita a forma NUVEMSHOP (pago externamente pelo checkout do canal)', () => {
    const result = PagamentoRequestSchema.safeParse({ forma_pagamento: 'NUVEMSHOP', valor: '100.00' })
    expect(result.success).toBe(true)
  })
})

// Regras por canal de origem (espelham o contrato do backend).
describe('CriarPedidoSchema — origem_canal / pedido_externo_id', () => {
  const base = {
    cliente_id: null,
    desconto: '0.00',
    itens: [{ variante_id: '11111111-1111-1111-1111-111111111111', quantidade: 1, desconto_item: '0.00' }],
    pagamentos: [{ forma_pagamento: 'DINHEIRO', valor: '100.00' }],
  }

  it('assume origem_canal PDV quando omitido', () => {
    const result = CriarPedidoSchema.safeParse(base)
    expect(result.success).toBe(true)
    if (result.success) expect(result.data.origem_canal).toBe('PDV')
  })

  it('rejeita origem_canal desconhecida', () => {
    expect(CriarPedidoSchema.safeParse({ ...base, origem_canal: 'INSTAGRAM' }).success).toBe(false)
  })

  it('PDV: rejeita pedido_externo_id', () => {
    const result = CriarPedidoSchema.safeParse({ ...base, origem_canal: 'PDV', pedido_externo_id: '1024' })
    expect(result.success).toBe(false)
    if (!result.success) expect(result.error.issues[0].path).toEqual(['pedido_externo_id'])
  })

  it('NUVEMSHOP: exige pedido_externo_id', () => {
    const result = CriarPedidoSchema.safeParse({
      ...base,
      origem_canal: 'NUVEMSHOP',
      pagamentos: [{ forma_pagamento: 'NUVEMSHOP', valor: '100.00' }],
    })
    expect(result.success).toBe(false)
    if (!result.success) expect(result.error.issues[0].path).toEqual(['pedido_externo_id'])
  })

  it('NUVEMSHOP: aceita com pedido_externo_id e faz trim', () => {
    const result = CriarPedidoSchema.safeParse({
      ...base,
      origem_canal: 'NUVEMSHOP',
      pedido_externo_id: '  1024 ',
      pagamentos: [{ forma_pagamento: 'NUVEMSHOP', valor: '100.00' }],
    })
    expect(result.success).toBe(true)
    if (result.success) expect(result.data.pedido_externo_id).toBe('1024')
  })

  it('WHATSAPP: aceita sem pedido_externo_id', () => {
    const result = CriarPedidoSchema.safeParse({ ...base, origem_canal: 'WHATSAPP' })
    expect(result.success).toBe(true)
  })

  it('WHATSAPP: rejeita pedido_externo_id (como o PDV)', () => {
    const result = CriarPedidoSchema.safeParse({ ...base, origem_canal: 'WHATSAPP', pedido_externo_id: 'Maria 1199' })
    expect(result.success).toBe(false)
    if (!result.success) expect(result.error.issues[0].path).toEqual(['pedido_externo_id'])
  })

  it('NUVEMSHOP: rejeita pedido_externo_id vazio ou com mais de 100 caracteres', () => {
    const nuvemshop = { ...base, origem_canal: 'NUVEMSHOP', pagamentos: [{ forma_pagamento: 'NUVEMSHOP', valor: '100.00' }] }
    expect(CriarPedidoSchema.safeParse({ ...nuvemshop, pedido_externo_id: '   ' }).success).toBe(false)
    expect(CriarPedidoSchema.safeParse({ ...nuvemshop, pedido_externo_id: 'x'.repeat(101) }).success).toBe(false)
    expect(CriarPedidoSchema.safeParse({ ...nuvemshop, pedido_externo_id: 'x'.repeat(100) }).success).toBe(true)
  })
})

describe('respostas de pedido — origem_canal / pedido_externo_id', () => {
  const pedido = {
    id: 'p1',
    numero: '000001',
    usuario_id: 'u1',
    status: 'CONFIRMADO',
    origem_canal: 'NUVEMSHOP',
    pedido_externo_id: '1024',
    subtotal: '100.00',
    desconto: '0.00',
    valor_total: '100.00',
    criado_em: '2026-09-21T10:00:00Z',
  }

  it('lista: lê origem_canal e pedido_externo_id (string ou null)', () => {
    const result = PedidoListResponseSchema.safeParse({
      data: [pedido, { ...pedido, id: 'p2', origem_canal: 'PDV', pedido_externo_id: null }],
      pagination: { total: 2, page: 1, per_page: 20 },
    })
    expect(result.success).toBe(true)
    if (result.success) {
      expect(result.data.data[0]).toMatchObject({ origem_canal: 'NUVEMSHOP', pedido_externo_id: '1024' })
      expect(result.data.data[1].pedido_externo_id).toBeNull()
    }
  })

  it('detalhe: aceita canal desconhecido sem quebrar e rejeita resposta sem origem_canal', () => {
    const detalhe = { ...pedido, itens: [], pagamentos: [] }
    expect(PedidoDetalheResponseSchema.safeParse({ ...detalhe, origem_canal: 'NOVO_CANAL' }).success).toBe(true)
    expect(PedidoDetalheResponseSchema.safeParse({ ...detalhe, origem_canal: undefined }).success).toBe(false)
  })
})
