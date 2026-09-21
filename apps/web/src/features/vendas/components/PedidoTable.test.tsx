import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { axe } from 'jest-axe'
import { PedidoTable } from './PedidoTable'
import { makePedido } from '../__fixtures__/pedido.fixtures'

function renderTable(pedidos = [makePedido()]) {
  return render(
    <MemoryRouter>
      <PedidoTable pedidos={pedidos} />
    </MemoryRouter>,
  )
}

// Coluna/badge de canal na listagem de pedidos.
describe('PedidoTable — canal', () => {
  it('exibe a coluna Canal com o badge de cada pedido', () => {
    renderTable([
      makePedido({ id: 'p1', numero: '000001', origem_canal: 'PDV' }),
      makePedido({ id: 'p2', numero: '000002', origem_canal: 'WHATSAPP' }),
      makePedido({ id: 'p3', numero: '000003', origem_canal: 'NUVEMSHOP' }),
    ])

    expect(screen.getByRole('columnheader', { name: 'Canal' })).toBeInTheDocument()
    const linhas = screen.getAllByRole('row').slice(1)
    expect(within(linhas[0]).getByText('PDV')).toBeInTheDocument()
    expect(within(linhas[1]).getByText('WhatsApp')).toBeInTheDocument()
    expect(within(linhas[2]).getByText('Nuvemshop')).toBeInTheDocument()
  })

  it('mostra o número externo ao lado do badge quando existir', () => {
    renderTable([
      makePedido({ id: 'p1', origem_canal: 'NUVEMSHOP', pedido_externo_id: '1024' }),
      makePedido({ id: 'p2', numero: '000002', origem_canal: 'PDV', pedido_externo_id: null }),
    ])

    const linhas = screen.getAllByRole('row').slice(1)
    expect(within(linhas[0]).getByText('#1024')).toBeInTheDocument()
    expect(within(linhas[1]).queryByText(/^#/)).not.toBeInTheDocument()
  })

  it('exibe um canal desconhecido como veio da API, sem quebrar', () => {
    renderTable([makePedido({ origem_canal: 'MARKETPLACE_X' })])

    expect(screen.getByText('MARKETPLACE_X')).toBeInTheDocument()
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = renderTable([makePedido({ origem_canal: 'NUVEMSHOP', pedido_externo_id: '1024' })])
    const results = await axe(container)
    expect(results.violations).toEqual([])
  })
})
