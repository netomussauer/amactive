import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HeroBanner } from './HeroBanner'

describe('HeroBanner', () => {
  it('apresenta o título como texto real, não como imagem', () => {
    render(<HeroBanner />)

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('SEU RITMO.')
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('SEU ESTILO.')
  })

  it('o botão leva à coleção', () => {
    render(<HeroBanner />)

    expect(screen.getByRole('link', { name: /conheça a coleção/i })).toHaveAttribute('href', '#colecao')
  })

  it('mostra a foto da modelo e o logotipo como assets separados, com texto alternativo', () => {
    render(<HeroBanner />)

    const modelo = screen.getByAltText(/modelo praticando corrida/i)
    expect(modelo).toHaveAttribute('src', '/brand/hero-modelo-1200.webp')
    expect(modelo.getAttribute('srcset')).toContain('/brand/hero-modelo-800.webp 800w')
    expect(screen.getByAltText('AMACTIVE')).toHaveAttribute('src', '/brand/amactive-logo-white.png')
  })

  it('lista os quatro benefícios da arte', () => {
    render(<HeroBanner />)

    for (const texto of ['Tecnologia e conforto', 'Respirabilidade e leveza', 'Performance que move', 'Feito para você']) {
      expect(screen.getByText(texto)).toBeInTheDocument()
    }
  })
})
