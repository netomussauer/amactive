import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { ProdutoPage } from './ProdutoPage'
import type { ProdutoDetalheLoja } from '../schemas/loja.schema'

// Produto com fotos SÓ na cor Preto. Azul existe como variante, mas ainda não tem foto.
const produto: ProdutoDetalheLoja = {
  id: 'p-1',
  nome: 'Legging Teste',
  marca: 'AMACTIVE',
  categoria: null,
  desconto_percentual: null,
  preco_a_partir_de: '99.90',
  imagem_principal_url: '/media/preto.jpg',
  cores: ['Azul', 'Preto'],
  descricao: null,
  variantes: [
    { id: 'v-azul', sku: 'AZ-M', tamanho: 'M', cor: 'Azul', preco_unitario: '99.90', preco_cheio: '99.90', disponivel: 2 },
    { id: 'v-preto', sku: 'PR-M', tamanho: 'M', cor: 'Preto', preco_unitario: '99.90', preco_cheio: '99.90', disponivel: 2 },
  ],
  imagens: [{ cor: 'Preto', url: '/media/preto.jpg', principal: true }],
}

vi.mock('../hooks/useLojaQueries', () => ({
  useProdutoLoja: () => ({ isPending: false, isError: false, data: produto }),
  useRelacionadosLoja: () => ({ data: undefined }),
}))

function renderizar() {
  return render(
    <MemoryRouter initialEntries={['/produtos/p-1']}>
      <Routes>
        <Route path="/produtos/:produtoId" element={<ProdutoPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProdutoPage — foto por cor', () => {
  it('abre na primeira cor que já tem foto', () => {
    renderizar()

    // A URL final inclui a origem da API (getMediaUrl); conferimos o caminho da foto.
    expect(screen.getByRole('img', { name: /Legging Teste — Preto/ }).getAttribute('src')).toContain('/media/preto.jpg')
  })

  it('ao escolher uma cor sem foto, não mostra a foto de outra cor', async () => {
    const user = userEvent.setup()
    renderizar()

    await user.click(screen.getByRole('button', { name: 'Azul' }))

    expect(screen.queryByRole('img', { name: /Legging Teste — Azul/ })).toBeNull()
    expect(screen.queryByRole('img', { name: /Legging Teste — Preto/ })).toBeNull()
    expect(screen.getByText('Foto de Azul em breve')).toBeInTheDocument()
  })
})
