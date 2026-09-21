import type { Pedido, PedidoDetalhe } from '../types/pedido.types'

export function makePedido(overrides: Partial<Pedido> = {}): Pedido {
  return {
    id: 'pedido-1',
    numero: '000001',
    cliente_id: null,
    usuario_id: 'usuario-1',
    status: 'CONFIRMADO',
    origem_canal: 'PDV',
    pedido_externo_id: null,
    subtotal: '100.00',
    desconto: '0.00',
    valor_total: '100.00',
    criado_em: '2026-09-21T13:00:00Z',
    confirmado_em: '2026-09-21T13:00:00Z',
    ...overrides,
  }
}

export function makePedidoDetalhe(overrides: Partial<PedidoDetalhe> = {}): PedidoDetalhe {
  return {
    ...makePedido(),
    itens: [
      {
        id: 'item-1',
        variante_id: 'variante-1',
        sku: 'LEG-CORAL-M',
        quantidade: 1,
        preco_unitario: '100.00',
        desconto_item: '0.00',
        subtotal: '100.00',
      },
    ],
    pagamentos: [{ id: 'pagamento-1', forma_pagamento: 'DINHEIRO', valor: '100.00' }],
    ...overrides,
  }
}
