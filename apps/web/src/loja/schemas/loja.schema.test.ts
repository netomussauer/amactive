import { describe, expect, it } from 'vitest'
import { PedidoCheckoutLojaSchema, ProdutoDetalheLojaSchema, ProdutoListaLojaSchema } from './loja.schema'
import { CheckoutFormSchema } from './checkout.schema'

// Formato real que a API devolve (serialização de Decimal como string — ver
// a regressão de desconto_percentual em docs/vitrine-online.md).
const variante = {
  id: 'a1b2',
  sku: 'LEG-PRE-M',
  tamanho: 'M',
  cor: 'Preto',
  preco_unitario: '89.91',
  preco_cheio: '99.90',
  disponivel: 4,
}

const produtoDetalhe = {
  id: 'p-1',
  nome: 'Legging Fitness',
  marca: 'AMACTIVE',
  categoria: { id: 'c-1', nome: 'Leggings' },
  desconto_percentual: '10.00',
  preco_a_partir_de: '89.91',
  imagem_principal_url: '/media/produtos/p-1/x.jpg',
  cores: ['Preto'],
  descricao: null,
  variantes: [variante],
  imagens: [{ cor: 'Preto', url: '/media/produtos/p-1/x.jpg', principal: true }],
}

describe('schemas da vitrine (contrato com a API)', () => {
  it('aceita o detalhe de produto no formato real, com desconto como string', () => {
    expect(ProdutoDetalheLojaSchema.parse(produtoDetalhe).desconto_percentual).toBe('10.00')
  })

  it('rejeita desconto numérico (regressão: a API envia Decimal como string)', () => {
    expect(() =>
      ProdutoDetalheLojaSchema.parse({ ...produtoDetalhe, desconto_percentual: 10 }),
    ).toThrow()
  })

  it('aceita a listagem paginada', () => {
    const lista = ProdutoListaLojaSchema.parse({
      data: [produtoDetalhe],
      pagination: { total: 1, page: 1, per_page: 24 },
    })
    expect(lista.data).toHaveLength(1)
  })

  it('aceita a confirmação de pedido do checkout', () => {
    const pedido = PedidoCheckoutLojaSchema.parse({
      numero: 'PED-000001',
      status: 'PENDENTE',
      subtotal: '179.82',
      valor_total: '179.82',
      reservado_ate: '2026-10-06T12:00:00Z',
      itens: [
        { sku: 'LEG-PRE-M', descricao: 'Legging Fitness Preto M', quantidade: 2, preco_unitario: '89.91', subtotal: '179.82' },
      ],
    })
    expect(pedido.numero).toBe('PED-000001')
  })
})

describe('CheckoutFormSchema', () => {
  const valido = { nome: 'Ana Cliente', telefone: '(11) 99999-0001', observacao: '' }

  it('aceita nome e telefone com DDD', () => {
    expect(CheckoutFormSchema.safeParse(valido).success).toBe(true)
  })

  it('exige um telefone com 10 a 13 dígitos', () => {
    expect(CheckoutFormSchema.safeParse({ ...valido, telefone: '99999' }).success).toBe(false)
    expect(CheckoutFormSchema.safeParse({ ...valido, telefone: '1199999999999999' }).success).toBe(false)
  })

  it('exige um nome com pelo menos 2 caracteres, ignorando espaços nas pontas', () => {
    expect(CheckoutFormSchema.safeParse({ ...valido, nome: '  A ' }).success).toBe(false)
    expect(CheckoutFormSchema.safeParse({ ...valido, nome: '  Ana ' }).success).toBe(true)
  })
})
