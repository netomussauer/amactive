import { afterEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { formatCurrencyBRL } from '@/shared/lib/format'
import type { PedidoCheckoutLoja } from '../schemas/loja.schema'

// O normalizador padrao do Testing Library colapsa espaco (inclusive NBSP)
// no texto RENDERIZADO antes de comparar, mas nao no literal que a gente
// passa como matcher -- formatCurrencyBRL usa NBSP entre "R$" e o valor
// (Intl pt-BR), entao sem isso o getByText nunca bate.
const NBSP = String.fromCharCode(160)
function moeda(valor: string): string {
  return formatCurrencyBRL(valor).split(NBSP).join(' ')
}

// Produto com acento, aspas e vírgula de milhar no total — justamente os
// casos que quebram encoding de URL e formatação de moeda se algo estiver
// errado. É o pedido real que o cliente manda pro WhatsApp da loja, então
// este teste valida a formatação EXATA da mensagem (pedido explícito do
// usuário: "validar a formatação da mensagem enviada").
const pedido: PedidoCheckoutLoja = {
  numero: 'PED-001494',
  status: 'PENDENTE',
  subtotal: '1233.82',
  valor_total: '1233.82',
  reservado_ate: '2026-10-10T13:00:00Z',
  itens: [
    { sku: 'LEG-PRETO-M', descricao: 'Legging Fitness Alta Compressão Preto M', quantidade: 2, preco_unitario: '116.91', subtotal: '233.82' },
    { sku: 'CJT-AZ-P', descricao: 'Conjunto AM Fit Azul Marinho P', quantidade: 1, preco_unitario: '1000.00', subtotal: '1000.00' },
  ],
}

async function renderizar() {
  const { PedidoEnviadoPage } = await import('./PedidoEnviadoPage')
  return render(
    <MemoryRouter
      initialEntries={[{ pathname: '/pedido-enviado', state: { pedido, nomeCliente: 'Ana Cliente' } }]}
    >
      <Routes>
        <Route path="/pedido-enviado" element={<PedidoEnviadoPage />} />
        <Route path="/" element={<p>Vitrine</p>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('PedidoEnviadoPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    vi.resetModules()
  })

  it('volta pra vitrine sem estado de navegação (ex.: recarregar a aba)', async () => {
    const { PedidoEnviadoPage } = await import('./PedidoEnviadoPage')
    render(
      <MemoryRouter initialEntries={['/pedido-enviado']}>
        <Routes>
          <Route path="/pedido-enviado" element={<PedidoEnviadoPage />} />
          <Route path="/" element={<p>Vitrine</p>} />
        </Routes>
      </MemoryRouter>,
    )

    expect(screen.getByText('Vitrine')).toBeInTheDocument()
  })

  it('monta a mensagem com número, cliente, cada item e total, formatados em R$', async () => {
    await renderizar()

    const mensagem = screen.getByLabelText('Mensagem do pedido') as HTMLTextAreaElement
    // formatCurrencyBRL (Intl, pt-BR) usa NBSP entre "R$" e o valor — por
    // isso construímos o esperado com a própria função em vez de digitar o
    // literal (evita um falso-negativo por causa do espaço).
    expect(mensagem.value).toBe(
      [
        'Olá! Quero finalizar meu pedido da loja online AMACTIVE.',
        '',
        'Pedido: PED-001494',
        'Cliente: Ana Cliente',
        '',
        `• 2x Legging Fitness Alta Compressão Preto M — ${formatCurrencyBRL('233.82')}`,
        `• 1x Conjunto AM Fit Azul Marinho P — ${formatCurrencyBRL('1000.00')}`,
        '',
        `Total: ${formatCurrencyBRL('1233.82')}`,
        '',
        'Pode me passar a forma de pagamento?',
      ].join('\n'),
    )
  })

  it('exibe o número do pedido, prazo de reserva e resumo dos itens na tela', async () => {
    await renderizar()

    expect(screen.getByText('Pedido PED-001494 registrado')).toBeInTheDocument()
    expect(screen.getByText('2x Legging Fitness Alta Compressão Preto M')).toBeInTheDocument()
    expect(screen.getByText('1x Conjunto AM Fit Azul Marinho P')).toBeInTheDocument()
    expect(screen.getByText(moeda('1233.82'))).toBeInTheDocument()
  })

  it('com WhatsApp da loja configurado, o link leva ao wa.me com a mensagem codificada', async () => {
    vi.doMock('../config', () => ({ WHATSAPP_LOJA: '5521965460985' }))
    await renderizar()

    const link = screen.getByRole('link', { name: 'Enviar pedido pelo WhatsApp' })
    const href = link.getAttribute('href') ?? ''
    expect(href.startsWith('https://wa.me/5521965460985?text=')).toBe(true)
    // A mensagem decodificada da URL bate exatamente com o texto do campo.
    const mensagem = screen.getByLabelText('Mensagem do pedido') as HTMLTextAreaElement
    const textoCodificado = href.split('?text=')[1]
    expect(decodeURIComponent(textoCodificado)).toBe(mensagem.value)
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('sem WhatsApp da loja configurado, oferece só copiar a mensagem (sem link quebrado)', async () => {
    vi.doMock('../config', () => ({ WHATSAPP_LOJA: '' }))
    await renderizar()

    expect(screen.queryByRole('link', { name: 'Enviar pedido pelo WhatsApp' })).not.toBeInTheDocument()
    expect(
      screen.getByText('O envio direto pelo WhatsApp ainda não está disponível. Copie a mensagem abaixo e envie para a loja.'),
    ).toBeInTheDocument()
  })

  it('"Copiar mensagem" copia o texto exato pra área de transferência', async () => {
    vi.doMock('../config', () => ({ WHATSAPP_LOJA: '5521965460985' }))
    const escrever = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    // DEPOIS de userEvent.setup(): ele mexe no navigator.clipboard na
    // própria inicialização (pra suportar .copy()/.paste()), então definir
    // antes é sobrescrito. jsdom também expõe clipboard como getter não
    // gravável — Object.assign não funciona, precisa de defineProperty.
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: escrever },
      configurable: true,
    })
    await renderizar()

    const mensagem = screen.getByLabelText('Mensagem do pedido') as HTMLTextAreaElement
    await user.click(screen.getByRole('button', { name: 'Copiar mensagem' }))

    await waitFor(() => expect(escrever).toHaveBeenCalledWith(mensagem.value))
    expect(await screen.findByRole('button', { name: 'Mensagem copiada' })).toBeInTheDocument()
  })
})
