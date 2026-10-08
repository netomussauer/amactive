import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { CatalogoPage } from './CatalogoPage'
import type { ProdutoResumoLoja } from '../schemas/loja.schema'

const produto: ProdutoResumoLoja = {
  id: 'p-1',
  nome: 'Legging Teste',
  marca: 'AMACTIVE',
  categoria: null,
  imagem_principal_url: '/media/p-1.jpg',
  desconto_percentual: '10.00',
  cores: ['Preto'],
  preco_a_partir_de: '99.90',
}

const listaComUmProduto = {
  data: [produto],
  pagination: { total: 1, page: 1, per_page: 24 },
}

vi.mock('../hooks/useLojaQueries', () => ({
  useCategoriasLoja: () => ({ data: [] }),
  useOpcoesFiltroLoja: () => ({ data: { cores: [], tamanhos: [] } }),
  // Chamado duas vezes (destaques e grade principal) com filtros diferentes
  // — mesma lista nas duas, só precisamos que ambas renderizem.
  useProdutosLoja: () => ({ isPending: false, data: listaComUmProduto }),
}))

function renderizar() {
  return render(
    <MemoryRouter>
      <CatalogoPage />
    </MemoryRouter>,
  )
}

describe('CatalogoPage — grades de produto', () => {
  it('usa os mesmos breakpoints de colunas em "Em destaque" e na grade principal', () => {
    // Bug real (2026-10-08): ProdutoCard escala a altura da foto com a
    // largura da coluna (aspect-[3/4]) — se "Em destaque" e a grade
    // principal ("Categorias") tiverem números de colunas diferentes no
    // mesmo breakpoint, as fotos de uma seção parecem maiores que as da
    // outra ao rolar a página, mesmo sendo o mesmo componente ProdutoCard.
    renderizar()

    const tituloDestaques = screen.getByRole('heading', { name: 'Em destaque' })
    const gradeDestaques = tituloDestaques.nextElementSibling
    const tituloCategorias = screen.getByRole('heading', { name: 'Categorias' })
    // A grade principal não é irmã direta do título (tem a busca no meio) —
    // localizamos pelo papel de "group" rotulado como filtros/ordenação e
    // pegamos o grid de produtos, que é o container com os cards do produto.
    const cards = screen.getAllByRole('link', { name: /Legging Teste/ })
    const gradePrincipal = cards[cards.length - 1].parentElement

    expect(gradeDestaques).not.toBeNull()
    expect(gradePrincipal).not.toBeNull()
    expect(gradeDestaques?.className).toContain('md:grid-cols-3 lg:grid-cols-4')
    expect(gradePrincipal?.className).toContain('md:grid-cols-3 lg:grid-cols-4')
    expect(tituloCategorias).toBeInTheDocument()
  })
})
