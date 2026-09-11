import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GaleriaImagensProduto } from './GaleriaImagensProduto'
import type { Imagem } from '../types/imagem.types'

let mockData: { data: Imagem[] } | undefined
let mockIsLoading = false

vi.mock('../hooks/useImagensDoProduto', () => ({
  useImagensDoProduto: () => ({ data: mockData, isLoading: mockIsLoading }),
}))

vi.mock('./ImagemGaleriaCor', () => ({
  ImagemGaleriaCor: ({ cor, imagens }: { cor: string; imagens: Imagem[] }) => (
    <div data-testid={`galeria-${cor}`}>
      {cor} — {imagens.length} imagem(ns)
    </div>
  ),
}))

function makeImagem(overrides: Partial<Imagem> = {}): Imagem {
  return {
    id: 'img-1',
    produto_id: 'produto-1',
    cor: 'Coral',
    url: '/media/produtos/produto-1/foto.jpg',
    ordem: 0,
    principal: false,
    criado_em: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

describe('GaleriaImagensProduto', () => {
  it('mostra estado vazio quando o produto não tem cores ativas nem imagens', () => {
    mockData = { data: [] }
    mockIsLoading = false
    render(<GaleriaImagensProduto produtoId="produto-1" coresAtivas={[]} />)

    expect(screen.getByText(/nenhuma cor disponível/i)).toBeInTheDocument()
  })

  it('agrupa as imagens por cor e inclui cores ativas sem imagem ainda', () => {
    mockData = { data: [makeImagem({ cor: 'Coral' }), makeImagem({ id: 'img-2', cor: 'Coral', ordem: 1 })] }
    mockIsLoading = false
    render(<GaleriaImagensProduto produtoId="produto-1" coresAtivas={['Coral', 'Preto']} />)

    expect(screen.getByTestId('galeria-Coral')).toHaveTextContent('Coral — 2 imagem(ns)')
    expect(screen.getByTestId('galeria-Preto')).toHaveTextContent('Preto — 0 imagem(ns)')
  })

  it('exibe indicador de carregamento enquanto busca as imagens', () => {
    mockData = undefined
    mockIsLoading = true
    render(<GaleriaImagensProduto produtoId="produto-1" coresAtivas={['Coral']} />)

    expect(screen.getByRole('status')).toBeInTheDocument()
  })
})
