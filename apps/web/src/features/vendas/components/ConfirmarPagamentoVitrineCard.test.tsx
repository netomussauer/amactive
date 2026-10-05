import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { pedidoService } from '../services/pedido.service'
import type { PedidoDetalhe } from '../types/pedido.types'
import { ConfirmarPagamentoVitrineCard } from './ConfirmarPagamentoVitrineCard'

const pedido: PedidoDetalhe = {
  id: 'p-1',
  numero: 'PED-000001',
  cliente_id: 'c-1',
  usuario_id: null,
  status: 'PENDENTE',
  origem_canal: 'VITRINE',
  pedido_externo_id: null,
  subtotal: '200.00',
  desconto: '0.00',
  valor_total: '200.00',
  criado_em: '2026-10-05T12:00:00Z',
  confirmado_em: null,
  reservado_ate: '2026-10-06T12:00:00Z',
  itens: [],
  pagamentos: [],
}

function renderizar() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ConfirmarPagamentoVitrineCard pedido={pedido} />
    </QueryClientProvider>,
  )
}

describe('ConfirmarPagamentoVitrineCard', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('confirma com a forma escolhida e o valor total do pedido, após a confirmação do operador', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const confirmar = vi
      .spyOn(pedidoService, 'confirmarPagamentoVitrine')
      .mockResolvedValue({ ...pedido, status: 'CONFIRMADO', itens: [], pagamentos: [] })
    renderizar()

    await user.selectOptions(screen.getByLabelText('Forma de pagamento'), 'DINHEIRO')
    await user.click(screen.getByRole('button', { name: 'Confirmar pagamento' }))

    await waitFor(() =>
      expect(confirmar).toHaveBeenCalledWith('p-1', [
        { forma_pagamento: 'DINHEIRO', valor: '200.00' },
      ]),
    )
  })

  it('não envia nada se o operador cancelar a confirmação do navegador', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const confirmar = vi.spyOn(pedidoService, 'confirmarPagamentoVitrine')
    renderizar()

    await user.click(screen.getByRole('button', { name: 'Confirmar pagamento' }))

    expect(confirmar).not.toHaveBeenCalled()
  })
})
