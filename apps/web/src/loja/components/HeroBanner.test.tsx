import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { HeroBanner } from './HeroBanner'

describe('HeroBanner', () => {
  it('leva à coleção e tem texto alternativo descritivo', () => {
    render(<HeroBanner />)

    const link = screen.getByRole('link', { name: 'Ir para a coleção' })
    expect(link).toHaveAttribute('href', '#colecao')
    expect(screen.getByAltText(/SEU RITMO\. SEU ESTILO\./)).toBeInTheDocument()
  })

  it('oferece as duas larguras da arte para telas grandes e pequenas', () => {
    render(<HeroBanner />)

    const imagem = screen.getByAltText(/SEU RITMO/)
    expect(imagem.getAttribute('srcset')).toContain('/brand/hero-home-1536.webp 1536w')
    expect(imagem.getAttribute('srcset')).toContain('/brand/hero-home-1920.webp 1920w')
  })
})
