import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { PedidosListPage } from './PedidosListPage'
import { makePedido } from '../__fixtures__/pedido.fixtures'

const usePedidosMock = vi.fn()

vi.mock('../hooks/usePedidos', () => ({
  usePedidos: (filter: unknown) => usePedidosMock(filter),
}))

vi.mock('@/shared/hooks/usePermissoes', () => ({
  usePermissoes: () => ({ podeVenderNoPdv: true }),
}))

// Filtro por canal na listagem de pedidos.
describe('PedidosListPage — filtro por canal', () => {
  beforeEach(() => {
    usePedidosMock.mockReset()
    usePedidosMock.mockReturnValue({
      data: {
        data: [makePedido({ origem_canal: 'WHATSAPP' })],
        pagination: { total: 1, page: 1, per_page: 20 },
      },
      isLoading: false,
    })
  })

  function renderPage() {
    return render(
      <MemoryRouter>
        <PedidosListPage />
      </MemoryRouter>,
    )
  }

  it('lista todos os canais por padrão (sem origem_canal no filtro)', () => {
    renderPage()

    const [filter] = usePedidosMock.mock.calls[0]
    expect(filter).toMatchObject({ page: 1, per_page: 20 })
    expect(filter.origem_canal).toBeUndefined()
  })

  it('oferece Todos, PDV, WhatsApp e Nuvemshop no filtro de canal', () => {
    renderPage()

    const select = screen.getByLabelText('Canal')
    const opcoes = Array.from(select.querySelectorAll('option')).map((option) => option.textContent)
    expect(opcoes).toEqual(['Todos', 'PDV', 'WhatsApp', 'Nuvemshop'])
  })

  it('passa origem_canal ao hook ao escolher um canal e volta à primeira página', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.selectOptions(screen.getByLabelText('Canal'), 'NUVEMSHOP')

    const ultimoFiltro = usePedidosMock.mock.calls.at(-1)?.[0]
    expect(ultimoFiltro).toMatchObject({ origem_canal: 'NUVEMSHOP', page: 1 })
  })

  it('remove origem_canal do filtro ao voltar para Todos', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.selectOptions(screen.getByLabelText('Canal'), 'WHATSAPP')
    await user.selectOptions(screen.getByLabelText('Canal'), '')

    const ultimoFiltro = usePedidosMock.mock.calls.at(-1)?.[0]
    expect(ultimoFiltro.origem_canal).toBeUndefined()
  })

  it('exibe o badge de canal dos pedidos retornados', () => {
    renderPage()

    expect(screen.getByRole('columnheader', { name: 'Canal' })).toBeInTheDocument()
    // O badge convive com a opção "WhatsApp" do filtro — busca dentro da tabela.
    expect(screen.getAllByText('WhatsApp').length).toBeGreaterThanOrEqual(2)
  })
})
