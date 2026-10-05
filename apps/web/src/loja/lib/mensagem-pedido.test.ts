import { describe, expect, it } from 'vitest'
import { linkWhatsApp, montarMensagemPedido } from './mensagem-pedido'

describe('montarMensagemPedido', () => {
  const mensagem = montarMensagemPedido({
    numero: 'PED-000123',
    nomeCliente: 'Ana Cliente',
    itens: [
      { descricao: 'Legging Fitness Preto M', quantidade: 2, subtotal: '179.80' },
      { descricao: 'Top Power Branco P', quantidade: 1, subtotal: '69.90' },
    ],
    valorTotal: '249.70',
  })

  it('traz número do pedido, cliente, itens e total em moeda brasileira', () => {
    expect(mensagem).toContain('Pedido: PED-000123')
    expect(mensagem).toContain('Cliente: Ana Cliente')
    expect(mensagem).toContain('• 2x Legging Fitness Preto M')
    expect(mensagem).toContain('• 1x Top Power Branco P')
    expect(mensagem).toContain('Total: R$')
    expect(mensagem).toContain('249,70')
  })
})

describe('linkWhatsApp', () => {
  it('monta o link wa.me com só dígitos e a mensagem codificada', () => {
    const link = linkWhatsApp('+55 (11) 99999-0000', 'Olá & até já')

    expect(link).toBe('https://wa.me/5511999990000?text=Ol%C3%A1%20%26%20at%C3%A9%20j%C3%A1')
  })

  it('retorna null sem número configurado, para a tela oferecer copiar em vez de um link quebrado', () => {
    expect(linkWhatsApp('', 'qualquer')).toBeNull()
    expect(linkWhatsApp('   ', 'qualquer')).toBeNull()
  })
})
