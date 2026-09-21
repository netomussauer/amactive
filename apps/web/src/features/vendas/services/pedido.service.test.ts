import { beforeEach, describe, expect, it, vi } from 'vitest'
import { pedidoService } from './pedido.service'
import { makePedidoDetalhe } from '../__fixtures__/pedido.fixtures'

const apiClientMock = vi.fn()

vi.mock('@/shared/lib/api-client', () => ({
  apiClient: (...args: unknown[]) => apiClientMock(...args),
}))

const itemValido = { variante_id: '11111111-1111-1111-1111-111111111111', quantidade: 1, desconto_item: '0.00' }

// Contrato HTTP de /pedidos com os campos de canal.
describe('pedidoService — canal de origem', () => {
  beforeEach(() => {
    apiClientMock.mockReset()
  })

  it('list: inclui origem_canal na query só quando informado', async () => {
    apiClientMock.mockResolvedValue({ data: [], pagination: { total: 0, page: 1, per_page: 20 } })

    await pedidoService.list({ page: 1, origem_canal: 'WHATSAPP' })
    await pedidoService.list({ page: 1, origem_canal: undefined })

    expect(apiClientMock.mock.calls[0][0]).toBe('/pedidos?page=1&origem_canal=WHATSAPP')
    expect(apiClientMock.mock.calls[1][0]).toBe('/pedidos?page=1')
  })

  it('criar: envia origem_canal e pedido_externo_id no corpo do POST', async () => {
    apiClientMock.mockResolvedValue(makePedidoDetalhe({ origem_canal: 'NUVEMSHOP', pedido_externo_id: '1024' }))

    const criado = await pedidoService.criar({
      origem_canal: 'NUVEMSHOP',
      pedido_externo_id: '1024',
      desconto: '0.00',
      itens: [itemValido],
      pagamentos: [{ forma_pagamento: 'NUVEMSHOP', valor: '100.00' }],
    })

    const [path, options] = apiClientMock.mock.calls[0]
    expect(path).toBe('/pedidos')
    expect(JSON.parse(options.body)).toMatchObject({
      origem_canal: 'NUVEMSHOP',
      pedido_externo_id: '1024',
      pagamentos: [{ forma_pagamento: 'NUVEMSHOP', valor: '100.00' }],
    })
    expect(criado.pedido_externo_id).toBe('1024')
  })

  it.each(['PDV', 'WHATSAPP'] as const)('criar: não chama a API quando %s vem com pedido_externo_id', async (canal) => {
    await expect(
      pedidoService.criar({
        origem_canal: canal,
        pedido_externo_id: 'Maria 1199',
        desconto: '0.00',
        itens: [itemValido],
        pagamentos: [{ forma_pagamento: 'DINHEIRO', valor: '100.00' }],
      }),
    ).rejects.toThrow()

    expect(apiClientMock).not.toHaveBeenCalled()
  })

  it('criar: não chama a API quando NUVEMSHOP vem sem número do pedido', async () => {
    await expect(
      pedidoService.criar({
        origem_canal: 'NUVEMSHOP',
        desconto: '0.00',
        itens: [itemValido],
        pagamentos: [{ forma_pagamento: 'NUVEMSHOP', valor: '100.00' }],
      }),
    ).rejects.toThrow()

    expect(apiClientMock).not.toHaveBeenCalled()
  })
})
