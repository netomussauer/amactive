import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { PrecoPromocional } from './PrecoPromocional'

expect.extend(toHaveNoViolations)

describe('PrecoPromocional', () => {
  it('exibe apenas o preço normal quando não há promoção', () => {
    render(<PrecoPromocional precoOriginal="100.00" />)

    expect(screen.getByText('R$ 100,00')).toBeInTheDocument()
  })

  it('exibe apenas o preço normal quando preco_promocional é nulo', () => {
    render(<PrecoPromocional precoOriginal="100.00" precoPromocional={null} />)

    expect(screen.getByText('R$ 100,00')).toBeInTheDocument()
  })

  it('exibe preço original riscado, preço promocional em destaque e badge de desconto', () => {
    render(<PrecoPromocional precoOriginal="100.00" precoPromocional="85.00" descontoPercentual="15.00" />)

    expect(screen.getByText('R$ 100,00')).toHaveClass('line-through')
    expect(screen.getByText('R$ 85,00')).toBeInTheDocument()
    expect(screen.getByText('-15%')).toBeInTheDocument()
  })

  it('não exibe badge de desconto quando descontoPercentual não é informado', () => {
    render(<PrecoPromocional precoOriginal="100.00" precoPromocional="85.00" />)

    expect(screen.queryByText(/^-/)).not.toBeInTheDocument()
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(
      <PrecoPromocional precoOriginal="100.00" precoPromocional="85.00" descontoPercentual="15.00" />,
    )
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
