import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PdvPagamentoForm } from './PdvPagamentoForm'
import { useCarrinhoStore } from '../store/carrinho.store'
import { ApiError } from '@/shared/lib/api-client'

type MutateOptions = { onSuccess?: (pedido: unknown) => void; onError?: (error: unknown) => void }

const mutateMock = vi.fn((_dto: unknown, options?: MutateOptions) => {
  options?.onSuccess?.({ id: 'pedido-1', numero: '000001', valor_total: '100.00' })
})

let mockError: unknown = null

vi.mock('../hooks/useCriarPedido', () => ({
  useCriarPedido: () => ({ mutate: mutateMock, isPending: false, error: mockError }),
}))

// Testes do fluxo crítico de pagamento do PDV (soma de pagamentos, 422 de estoque).
describe('PdvPagamentoForm', () => {
  beforeEach(() => {
    mockError = null
    mutateMock.mockClear()
    useCarrinhoStore.getState().clear()
    useCarrinhoStore.getState().addItem({
      varianteId: 'variante-1',
      sku: 'LEG-CORAL-M',
      produtoNome: 'Legging Fitness',
      tamanho: 'M',
      cor: 'Coral',
      precoUnitario: '100.00',
      quantidade: 1,
      descontoItem: '0.00',
      estoqueDisponivel: 10,
    })
  })

  afterEach(() => {
    useCarrinhoStore.getState().clear()
  })

  it('confirma a venda quando a soma dos pagamentos bate com o total', async () => {
    const user = userEvent.setup()
    const onConfirmado = vi.fn()

    render(<PdvPagamentoForm subtotal={100} onConfirmado={onConfirmado} />)

    await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

    expect(mutateMock).toHaveBeenCalledTimes(1)
    const [dto] = mutateMock.mock.calls[0]
    expect(dto).toMatchObject({
      itens: [{ variante_id: 'variante-1', quantidade: 1, desconto_item: '0.00' }],
    })
    expect(onConfirmado).toHaveBeenCalledWith({ id: 'pedido-1', numero: '000001', valor_total: '100.00' })
  })

  it('exibe erro inline quando a soma dos pagamentos diverge do total e não confirma a venda', async () => {
    const user = userEvent.setup()
    const onConfirmado = vi.fn()

    render(<PdvPagamentoForm subtotal={100} onConfirmado={onConfirmado} />)

    const valorInput = screen.getByLabelText(/valor da forma de pagamento 1/i)
    await user.clear(valorInput)
    await user.type(valorInput, '50.00')

    await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

    expect(await screen.findByText(/precisa ser igual ao total a pagar/i)).toBeInTheDocument()
    expect(mutateMock).not.toHaveBeenCalled()
  })

  it('envia o desconto_item calculado do item promocional e mantém o total exibido consistente com o payload', async () => {
    const user = userEvent.setup()
    const onConfirmado = vi.fn()

    // Item com preço promocional já refletido no desconto_item (ver
    // PdvBuscaProduto/carrinho.store) — subtotal com desconto: 200 - 30 = 170.
    useCarrinhoStore.getState().clear()
    useCarrinhoStore.getState().addItem({
      varianteId: 'variante-promo',
      sku: 'LEG-CORAL-P',
      produtoNome: 'Legging Fitness',
      tamanho: 'P',
      cor: 'Coral',
      precoUnitario: '100.00',
      quantidade: 2,
      descontoItem: '30.00',
      estoqueDisponivel: 10,
      precoPromocional: '85.00',
      descontoPercentual: '15.00',
    })

    render(<PdvPagamentoForm subtotal={170} onConfirmado={onConfirmado} />)

    // O valor padrão da forma de pagamento já nasce igual ao subtotal com desconto.
    expect(screen.getByLabelText(/valor da forma de pagamento 1/i)).toHaveValue('170.00')
    // Subtotal, "Total a pagar" e "Total informado nos pagamentos" todos batem em R$ 170,00.
    expect(screen.getAllByText('R$ 170,00')).toHaveLength(3)

    await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

    expect(mutateMock).toHaveBeenCalledTimes(1)
    const [dto] = mutateMock.mock.calls[0]
    expect(dto).toMatchObject({
      itens: [{ variante_id: 'variante-promo', quantidade: 2, desconto_item: '30.00' }],
      pagamentos: [{ forma_pagamento: 'DINHEIRO', valor: '170.00' }],
    })
  })

  it('exibe mensagem amigável de estoque insuficiente em erro 422', () => {
    mockError = new ApiError('Erro de validação', 422, 'Estoque insuficiente para a variante X')

    render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

    expect(screen.getByText(/estoque insuficiente para um ou mais itens/i)).toBeInTheDocument()
  })
})

// Canais de venda (PDV / WhatsApp / Nuvemshop): campos, forma de pagamento e payload.
describe('PdvPagamentoForm — canais de venda', () => {
  beforeEach(() => {
    mockError = null
    mutateMock.mockClear()
    useCarrinhoStore.getState().clear()
    useCarrinhoStore.getState().addItem({
      varianteId: 'variante-1',
      sku: 'LEG-CORAL-M',
      produtoNome: 'Legging Fitness',
      tamanho: 'M',
      cor: 'Coral',
      precoUnitario: '100.00',
      quantidade: 1,
      descontoItem: '0.00',
      estoqueDisponivel: 10,
    })
  })

  afterEach(() => {
    useCarrinhoStore.getState().clear()
  })

  function formasDisponiveis(): string[] {
    const select = screen.getByLabelText(/^forma de pagamento 1$/i)
    return Array.from(select.querySelectorAll('option')).map((option) => option.getAttribute('value') ?? '')
  }

  describe('canal PDV (padrão)', () => {
    it('não exibe campo de número do pedido nem a forma NUVEMSHOP', () => {
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      expect(screen.queryByLabelText(/pedido na nuvemshop/i)).not.toBeInTheDocument()
      expect(screen.queryByLabelText(/referência/i)).not.toBeInTheDocument()
      expect(formasDisponiveis()).toEqual(['DINHEIRO', 'PIX', 'CARTAO_DEBITO', 'CARTAO_CREDITO'])
    })

    it('envia origem_canal PDV sem pedido_externo_id', async () => {
      const user = userEvent.setup()
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

      const [dto] = mutateMock.mock.calls[0]
      expect(dto).toMatchObject({ origem_canal: 'PDV', pagamentos: [{ forma_pagamento: 'DINHEIRO', valor: '100.00' }] })
      expect(dto).not.toHaveProperty('pedido_externo_id')
    })
  })

  describe('canal WhatsApp', () => {
    beforeEach(() => {
      useCarrinhoStore.getState().setOrigemCanal('WHATSAPP')
    })

    it('não exibe campo de número/referência, mantém as formas comuns (sem NUVEMSHOP) e orienta a usar cliente e Observação', () => {
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      expect(screen.queryByLabelText(/referência/i)).not.toBeInTheDocument()
      expect(screen.queryByLabelText(/nº do pedido/i)).not.toBeInTheDocument()
      expect(formasDisponiveis()).not.toContain('NUVEMSHOP')
      expect(screen.getByText(/seletor de cliente no carrinho e o campo observação/i)).toBeInTheDocument()
    })

    it('confirma e nunca envia pedido_externo_id', async () => {
      const user = userEvent.setup()
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      await user.type(screen.getByLabelText(/observação/i), 'Maria - 11 99999-1199')
      await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

      const [dto] = mutateMock.mock.calls[0]
      expect(dto).toMatchObject({ origem_canal: 'WHATSAPP', observacao: 'Maria - 11 99999-1199' })
      expect(dto).not.toHaveProperty('pedido_externo_id')
    })

    it('continua exigindo que a soma dos pagamentos bata com o total', async () => {
      const user = userEvent.setup()
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      const valorInput = screen.getByLabelText(/valor da forma de pagamento 1/i)
      await user.clear(valorInput)
      await user.type(valorInput, '40.00')
      await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

      expect(await screen.findByText(/precisa ser igual ao total a pagar/i)).toBeInTheDocument()
      expect(mutateMock).not.toHaveBeenCalled()
    })
  })

  describe('canal Nuvemshop', () => {
    beforeEach(() => {
      useCarrinhoStore.getState().setOrigemCanal('NUVEMSHOP')
    })

    it('exibe o número do pedido como obrigatório e o pagamento fixo, sem seletor de forma', () => {
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      expect(screen.getByLabelText(/nº do pedido na nuvemshop/i)).toHaveAttribute('aria-required', 'true')
      expect(screen.getByText(/pago externamente pelo checkout da nuvemshop/i)).toBeInTheDocument()
      expect(screen.queryByLabelText(/^forma de pagamento 1$/i)).not.toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /adicionar forma/i })).not.toBeInTheDocument()
    })

    it('bloqueia a confirmação e mostra erro inline quando o número está vazio', async () => {
      const user = userEvent.setup()
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

      expect(await screen.findByText(/informe o número do pedido na nuvemshop/i)).toBeInTheDocument()
      expect(mutateMock).not.toHaveBeenCalled()
    })

    it('envia origem_canal, número e pagamento NUVEMSHOP pelo total (com desconto)', async () => {
      const user = userEvent.setup()
      const onConfirmado = vi.fn()
      render(<PdvPagamentoForm subtotal={100} onConfirmado={onConfirmado} />)

      await user.type(screen.getByLabelText(/nº do pedido na nuvemshop/i), ' 1024 ')
      const desconto = screen.getByLabelText(/desconto no pedido/i)
      await user.clear(desconto)
      await user.type(desconto, '10.00')
      await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

      expect(mutateMock).toHaveBeenCalledTimes(1)
      const [dto] = mutateMock.mock.calls[0]
      expect(dto).toMatchObject({
        origem_canal: 'NUVEMSHOP',
        pedido_externo_id: '1024',
        desconto: '10.00',
        pagamentos: [{ forma_pagamento: 'NUVEMSHOP', valor: '90.00' }],
      })
      expect(onConfirmado).toHaveBeenCalled()
    })
  })

  describe('troca de canal', () => {
    it('ao entrar na Nuvemshop descarta pagamentos lançados; ao sair, volta às formas comuns e limpa o número, mantendo o carrinho', async () => {
      const user = userEvent.setup()
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      // Lança um pagamento misto no PDV.
      await user.selectOptions(screen.getByLabelText(/^forma de pagamento 1$/i), 'PIX')
      await user.click(screen.getByRole('button', { name: /adicionar forma/i }))
      expect(screen.getByLabelText(/^forma de pagamento 2$/i)).toBeInTheDocument()

      act(() => useCarrinhoStore.getState().setOrigemCanal('NUVEMSHOP'))
      expect(await screen.findByText(/pago externamente pelo checkout da nuvemshop/i)).toBeInTheDocument()
      expect(screen.queryByLabelText(/^forma de pagamento/i)).not.toBeInTheDocument()

      await user.type(screen.getByLabelText(/nº do pedido na nuvemshop/i), '1024')

      act(() => useCarrinhoStore.getState().setOrigemCanal('PDV'))

      // Pagamentos voltam a uma única linha padrão, sem NUVEMSHOP; nenhum campo de número.
      const forma1 = await screen.findByLabelText(/^forma de pagamento 1$/i)
      expect(forma1).toHaveValue('DINHEIRO')
      expect(screen.queryByLabelText(/^forma de pagamento 2$/i)).not.toBeInTheDocument()
      expect(screen.getByLabelText(/valor da forma de pagamento 1/i)).toHaveValue('100.00')
      expect(screen.queryByLabelText(/pedido na nuvemshop/i)).not.toBeInTheDocument()
      expect(useCarrinhoStore.getState().itens).toHaveLength(1)

      // O número digitado na Nuvemshop não vaza para uma venda de PDV.
      await user.click(screen.getByRole('button', { name: /confirmar venda/i }))
      const [dto] = mutateMock.mock.calls[0]
      expect(dto).toMatchObject({ origem_canal: 'PDV', pagamentos: [{ forma_pagamento: 'DINHEIRO', valor: '100.00' }] })
      expect(dto).not.toHaveProperty('pedido_externo_id')
    })

    it('entre PDV e WhatsApp mantém os pagamentos lançados e nenhum dos dois tem campo de número', async () => {
      const user = userEvent.setup()
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      await user.selectOptions(screen.getByLabelText(/^forma de pagamento 1$/i), 'PIX')

      act(() => useCarrinhoStore.getState().setOrigemCanal('WHATSAPP'))
      expect(await screen.findByText(/vendas do whatsapp não usam número de pedido/i)).toBeInTheDocument()
      expect(screen.getByLabelText(/^forma de pagamento 1$/i)).toHaveValue('PIX')
      expect(screen.queryByLabelText(/nº do pedido|referência/i)).not.toBeInTheDocument()

      act(() => useCarrinhoStore.getState().setOrigemCanal('PDV'))
      expect(await screen.findByLabelText(/^forma de pagamento 1$/i)).toHaveValue('PIX')
      expect(screen.queryByText(/vendas do whatsapp não usam número de pedido/i)).not.toBeInTheDocument()
    })

    it('sair da Nuvemshop para o WhatsApp não vaza o número digitado no payload', async () => {
      const user = userEvent.setup()
      useCarrinhoStore.getState().setOrigemCanal('NUVEMSHOP')
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      await user.type(screen.getByLabelText(/nº do pedido na nuvemshop/i), '1024')
      act(() => useCarrinhoStore.getState().setOrigemCanal('WHATSAPP'))
      await user.click(await screen.findByRole('button', { name: /confirmar venda/i }))

      const [dto] = mutateMock.mock.calls[0]
      expect(dto).toMatchObject({ origem_canal: 'WHATSAPP', pagamentos: [{ forma_pagamento: 'DINHEIRO', valor: '100.00' }] })
      expect(dto).not.toHaveProperty('pedido_externo_id')
    })

    it('limpa o erro de número obrigatório ao trocar de canal', async () => {
      const user = userEvent.setup()
      useCarrinhoStore.getState().setOrigemCanal('NUVEMSHOP')
      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      await user.click(screen.getByRole('button', { name: /confirmar venda/i }))
      expect(await screen.findByText(/informe o número do pedido na nuvemshop/i)).toBeInTheDocument()

      act(() => useCarrinhoStore.getState().setOrigemCanal('WHATSAPP'))

      expect(screen.queryByText(/informe o número do pedido na nuvemshop/i)).not.toBeInTheDocument()
    })
  })

  describe('pedido duplicado (409)', () => {
    it('mostra mensagem amigável no campo e mantém o carrinho', async () => {
      const user = userEvent.setup()
      useCarrinhoStore.getState().setOrigemCanal('NUVEMSHOP')
      mutateMock.mockImplementationOnce((_dto: unknown, options?: MutateOptions) => {
        options?.onError?.(new ApiError('Conflito', 409, 'Pedido NUVEMSHOP 1024 já registrado'))
      })
      const onConfirmado = vi.fn()

      render(<PdvPagamentoForm subtotal={100} onConfirmado={onConfirmado} />)
      await user.type(screen.getByLabelText(/nº do pedido na nuvemshop/i), '1024')
      await user.click(screen.getByRole('button', { name: /confirmar venda/i }))

      expect(await screen.findByText('Já existe um pedido Nuvemshop com o número 1024.')).toBeInTheDocument()
      expect(onConfirmado).not.toHaveBeenCalled()
      expect(useCarrinhoStore.getState().itens).toHaveLength(1)
      // O número digitado continua no campo para o operador corrigir.
      expect(screen.getByLabelText(/nº do pedido na nuvemshop/i)).toHaveValue('1024')
    })

    it('fora da Nuvemshop, um 409 continua aparecendo no aviso genérico (não há campo para marcar)', () => {
      useCarrinhoStore.getState().setOrigemCanal('WHATSAPP')
      mockError = new ApiError('Conflito', 409, 'Conflito inesperado no pedido')

      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      expect(screen.getByText('Conflito inesperado no pedido')).toBeInTheDocument()
    })

    it('não duplica a mensagem no aviso genérico quando o erro da mutation é 409 na Nuvemshop', () => {
      useCarrinhoStore.getState().setOrigemCanal('NUVEMSHOP')
      mockError = new ApiError('Conflito', 409, 'Pedido NUVEMSHOP 1024 já registrado')

      render(<PdvPagamentoForm subtotal={100} onConfirmado={vi.fn()} />)

      expect(screen.queryByText(/já registrado/i)).not.toBeInTheDocument()
    })
  })
})
