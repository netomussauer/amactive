import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PedidoDetalheCard } from './PedidoDetalheCard'
import { makePedidoDetalhe } from '../__fixtures__/pedido.fixtures'

// Canal e número externo no detalhe do pedido.
describe('PedidoDetalheCard — canal', () => {
  it('mostra o canal e o número do pedido na Nuvemshop, com o pagamento externo', () => {
    render(
      <PedidoDetalheCard
        pedido={makePedidoDetalhe({
          origem_canal: 'NUVEMSHOP',
          pedido_externo_id: '1024',
          pagamentos: [{ id: 'pg-1', forma_pagamento: 'NUVEMSHOP', valor: '100.00' }],
        })}
      />,
    )

    expect(screen.getByText('Nuvemshop')).toBeInTheDocument()
    expect(screen.getByText('Nº do pedido na Nuvemshop')).toBeInTheDocument()
    expect(screen.getByText('1024')).toBeInTheDocument()
    expect(screen.getByText('Nuvemshop (pago no checkout)')).toBeInTheDocument()
  })

  it('mostra só o canal WhatsApp, sem campo de número, quando não há pedido_externo_id', () => {
    render(<PedidoDetalheCard pedido={makePedidoDetalhe({ origem_canal: 'WHATSAPP', pedido_externo_id: null })} />)

    expect(screen.getByText('WhatsApp')).toBeInTheDocument()
    expect(screen.queryByText(/Nº do pedido/)).not.toBeInTheDocument()
  })

  it('mostra só o canal (sem campo de número) quando não há pedido_externo_id no PDV', () => {
    render(<PedidoDetalheCard pedido={makePedidoDetalhe({ origem_canal: 'PDV', pedido_externo_id: null })} />)

    expect(screen.getByText('PDV')).toBeInTheDocument()
    expect(screen.queryByText(/Nº do pedido/)).not.toBeInTheDocument()
  })
})
