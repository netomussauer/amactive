import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RelatoriosPage } from './RelatoriosPage'

const useRelatorioVendasMock = vi.fn()

vi.mock('../hooks/useRelatorioVendas', () => ({
  useRelatorioVendas: (filter: unknown) => useRelatorioVendasMock(filter),
}))
vi.mock('../hooks/useRelatorioProdutos', () => ({
  useRelatorioProdutos: () => ({ data: { data: [] }, isLoading: false }),
}))
vi.mock('../hooks/useRelatorioGiroEstoque', () => ({
  useRelatorioGiroEstoque: () => ({ data: { data: [] }, isLoading: false }),
}))

// Filtro de canal em "vendas por período".
describe('RelatoriosPage — filtro por canal', () => {
  beforeEach(() => {
    useRelatorioVendasMock.mockReset()
    useRelatorioVendasMock.mockReturnValue({ data: { data: [] }, isLoading: false })
  })

  it('não filtra por canal por padrão', () => {
    render(<RelatoriosPage />)

    const [filter] = useRelatorioVendasMock.mock.calls[0]
    expect(filter.origem_canal).toBeUndefined()
    expect(filter).toHaveProperty('data_inicio')
    expect(filter).toHaveProperty('data_fim')
  })

  it('envia origem_canal ao relatório de vendas ao escolher um canal', async () => {
    const user = userEvent.setup()
    render(<RelatoriosPage />)

    await user.selectOptions(screen.getByLabelText(/canal/i), 'NUVEMSHOP')

    expect(useRelatorioVendasMock.mock.calls.at(-1)?.[0]).toMatchObject({ origem_canal: 'NUVEMSHOP' })
  })
})
