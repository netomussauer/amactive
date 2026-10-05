import { describe, expect, it } from 'vitest'
import { render, screen, within } from '@testing-library/react'
import { ComoFunciona } from './ComoFunciona'

describe('ComoFunciona', () => {
  it('descreve os três passos reais da compra, em ordem', () => {
    render(<ComoFunciona />)

    const passos = within(screen.getByRole('list')).getAllByRole('listitem')
    expect(passos).toHaveLength(3)
    expect(passos[0]).toHaveTextContent('Escolha suas peças')
    expect(passos[1]).toHaveTextContent('Envie o pedido pelo WhatsApp')
    expect(passos[2]).toHaveTextContent('Combine pagamento e entrega')
  })
})
