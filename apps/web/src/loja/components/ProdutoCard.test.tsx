import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProdutoCard } from './ProdutoCard'
import type { ProdutoResumoLoja } from '../schemas/loja.schema'

// Bug real (2026-10-09): fotos com proporção natural diferente de 3:4
// (ex: 855×1280) faziam a caixa da foto crescer para a proporção DA FOTO em
// vez de respeitar aspect-[3/4] — o `min-height:auto` implícito de um item
// flex com conteúdo substituído (<img>) "vaza" através do aspect-ratio do
// pai. Reproduzido e confirmado com Chromium headless real (jsdom não
// executa layout CSS de verdade — aspect-ratio/flexbox não são calculados
// aqui, então este teste não mede pixels, só garante que as classes que
// corrigem o problema (min-h-0 min-w-0) continuam presentes).
const produtoComFoto: ProdutoResumoLoja = {
  id: 'p-1',
  nome: 'AM Intense',
  marca: 'AMACTIVE',
  categoria: null,
  imagem_principal_url: '/media/p-1.jpg',
  desconto_percentual: null,
  cores: ['Preto'],
  preco_a_partir_de: '149.99',
}

const produtoSemFoto: ProdutoResumoLoja = { ...produtoComFoto, id: 'p-2', imagem_principal_url: null }

function caixaDaFoto(nomeProduto: string) {
  return screen.getByRole('link', { name: new RegExp(nomeProduto) }).querySelector('.aspect-\\[3\\/4\\]')
}

describe('ProdutoCard', () => {
  it('a caixa da foto tem min-h-0 e min-w-0 (produto com foto)', () => {
    render(
      <MemoryRouter>
        <ProdutoCard produto={produtoComFoto} />
      </MemoryRouter>,
    )
    const caixa = caixaDaFoto('AM Intense')
    expect(caixa?.className).toContain('aspect-[3/4]')
    expect(caixa?.className).toContain('min-h-0')
    expect(caixa?.className).toContain('min-w-0')
  })

  it('a caixa da foto tem min-h-0 e min-w-0 (produto sem foto, "Sem imagem")', () => {
    render(
      <MemoryRouter>
        <ProdutoCard produto={produtoSemFoto} />
      </MemoryRouter>,
    )
    const caixa = caixaDaFoto('AM Intense')
    expect(caixa?.className).toContain('min-h-0')
    expect(caixa?.className).toContain('min-w-0')
    expect(screen.getByText('Sem imagem')).toBeInTheDocument()
  })
})
