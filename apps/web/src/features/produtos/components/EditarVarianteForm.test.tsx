import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EditarVarianteForm } from './EditarVarianteForm'

const variante = {
  sku: 'LEG-PRE-M',
  tamanho: 'M',
  cor: 'Preto',
  preco_venda: '99.90',
  preco_custo: '60.00',
}

describe('EditarVarianteForm', () => {
  it('envia o SKU corrigido e o tamanho, mantendo o restante', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<EditarVarianteForm variante={variante} onSubmit={onSubmit} onCancel={() => {}} />)

    const sku = screen.getByLabelText(/^SKU/)
    await user.clear(sku)
    await user.type(sku, 'LEG-PRE-MG-002')
    await user.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    await waitFor(() =>
      expect(onSubmit).toHaveBeenCalledWith({
        sku: 'LEG-PRE-MG-002',
        tamanho: 'M',
        cor: 'Preto',
        preco_venda: '99.90',
        preco_custo: '60.00',
      }),
    )
  })

  it('campo de custo vazio remove o custo (envia null)', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<EditarVarianteForm variante={variante} onSubmit={onSubmit} onCancel={() => {}} />)

    await user.clear(screen.getByLabelText(/^Preço de custo/))
    await user.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    await waitFor(() => expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ preco_custo: null })))
  })

  it('não envia preço fora do formato 0.00', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()
    render(<EditarVarianteForm variante={variante} onSubmit={onSubmit} onCancel={() => {}} />)

    const venda = screen.getByLabelText(/^Preço de venda/)
    await user.clear(venda)
    await user.type(venda, '99,90')
    await user.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    expect(await screen.findByText('Use o formato 0.00')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })
})
