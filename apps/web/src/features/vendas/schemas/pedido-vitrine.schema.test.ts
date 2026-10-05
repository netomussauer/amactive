import { describe, expect, it } from 'vitest'
import { PedidoListResponseSchema, PedidoResponseSchema } from './pedido.schema'
import { labelCanal } from '../lib/canal'

// Pedido da loja online no formato real: sem operador (usuario_id nulo) e com
// prazo de reserva. Antes da correção, `usuario_id: z.string()` derrubava a
// listagem inteira ao aparecer o primeiro pedido da vitrine.
const pedidoVitrine = {
  id: 'p-1',
  numero: 'PED-000001',
  cliente_id: 'c-1',
  usuario_id: null,
  status: 'PENDENTE',
  origem_canal: 'VITRINE',
  pedido_externo_id: null,
  subtotal: '200.00',
  desconto: '0.00',
  valor_total: '200.00',
  criado_em: '2026-10-05T12:00:00Z',
  confirmado_em: null,
  reservado_ate: '2026-10-06T12:00:00Z',
}

describe('pedido da vitrine na área administrativa', () => {
  it('aceita pedido sem operador (usuario_id nulo)', () => {
    expect(PedidoResponseSchema.parse(pedidoVitrine).usuario_id).toBeNull()
  })

  it('a listagem não quebra com um pedido da vitrine misturado aos demais', () => {
    const lista = PedidoListResponseSchema.parse({
      data: [pedidoVitrine],
      pagination: { total: 1, page: 1, per_page: 20 },
    })
    expect(lista.data[0].origem_canal).toBe('VITRINE')
  })

  it('exibe o canal da vitrine como "Loja online", sem entrar nas opções do PDV', () => {
    expect(labelCanal('VITRINE')).toBe('Loja online')
  })
})
