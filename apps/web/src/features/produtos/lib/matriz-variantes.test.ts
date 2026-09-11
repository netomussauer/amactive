import { describe, expect, it } from 'vitest'
import {
  atualizarCombo,
  gerarMatrizVariantes,
  gerarSkuVariante,
  removerCombo,
  TAMANHOS_SUGERIDOS,
} from './matriz-variantes'

describe('gerarSkuVariante', () => {
  it('gera SKU determinístico a partir das 3 primeiras letras do produto + cor + tamanho', () => {
    expect(gerarSkuVariante('Legging Fitness Alta Compressão', 'Coral', 'M')).toBe('LEG-CORAL-M')
  })

  it('remove acentos e espaços da cor', () => {
    expect(gerarSkuVariante('Top', 'Rosa Queimado', 'PP')).toBe('TOP-ROSAQUEIMADO-PP')
  })

  it('é determinístico: mesma entrada sempre gera o mesmo SKU', () => {
    const sku1 = gerarSkuVariante('Legging Fitness', 'Preto', 'G')
    const sku2 = gerarSkuVariante('Legging Fitness', 'Preto', 'G')
    expect(sku1).toBe(sku2)
  })

  it('usa fallback quando o nome do produto está vazio', () => {
    expect(gerarSkuVariante('', 'Preto', 'M')).toBe('PRD-PRETO-M')
  })
})

describe('gerarMatrizVariantes', () => {
  const base = {
    nomeProduto: 'Legging Fitness',
    cores: ['Coral', 'Preto'],
    tamanhos: ['P', 'M', 'G'],
    precoVendaBase: '129.90',
  }

  it('gera o produto cartesiano cor × tamanho', () => {
    const combos = gerarMatrizVariantes(base)
    expect(combos).toHaveLength(6)
    expect(combos.map((c) => `${c.cor}/${c.tamanho}`)).toEqual([
      'Coral/P',
      'Coral/M',
      'Coral/G',
      'Preto/P',
      'Preto/M',
      'Preto/G',
    ])
  })

  it('aplica o preço base a todas as combinações geradas', () => {
    const combos = gerarMatrizVariantes(base)
    expect(combos.every((c) => c.precoVenda === '129.90')).toBe(true)
  })

  it('gera SKU determinístico por combinação', () => {
    const combos = gerarMatrizVariantes(base)
    const coralM = combos.find((c) => c.cor === 'Coral' && c.tamanho === 'M')
    expect(coralM?.sku).toBe('LEG-CORAL-M')
  })

  it('ignora cores e tamanhos vazios ou duplicados (case-insensitive)', () => {
    const combos = gerarMatrizVariantes({
      ...base,
      cores: ['Coral', ' coral ', '', 'Preto'],
      tamanhos: ['M', 'M', ''],
    })
    expect(combos).toHaveLength(2)
  })

  it('preserva overrides de combos existentes ao regenerar (ex: nova cor adicionada)', () => {
    const primeiraGeracao = gerarMatrizVariantes({ ...base, cores: ['Coral'], tamanhos: ['M'] })
    const editado = atualizarCombo(primeiraGeracao, primeiraGeracao[0].id, { precoVenda: '99.90' })

    const segundaGeracao = gerarMatrizVariantes({
      ...base,
      cores: ['Coral', 'Preto'],
      tamanhos: ['M'],
      combosExistentes: editado,
    })

    expect(segundaGeracao).toHaveLength(2)
    const coral = segundaGeracao.find((c) => c.cor === 'Coral')
    expect(coral?.precoVenda).toBe('99.90') // override preservado
    const preto = segundaGeracao.find((c) => c.cor === 'Preto')
    expect(preto?.precoVenda).toBe('129.90') // novo combo usa o preço base
  })

  it('retorna lista vazia quando não há cores ou tamanhos', () => {
    expect(gerarMatrizVariantes({ ...base, cores: [], tamanhos: [] })).toEqual([])
  })
})

describe('removerCombo', () => {
  it('remove apenas a combinação informada (nem toda cor tem todo tamanho)', () => {
    const combos = gerarMatrizVariantes({
      nomeProduto: 'Top',
      cores: ['Coral', 'Preto'],
      tamanhos: ['P', 'M'],
      precoVendaBase: '79.90',
    })
    const alvo = combos.find((c) => c.cor === 'Preto' && c.tamanho === 'P')
    const restante = removerCombo(combos, alvo!.id)

    expect(restante).toHaveLength(3)
    expect(restante.some((c) => c.id === alvo!.id)).toBe(false)
  })
})

describe('atualizarCombo', () => {
  it('atualiza somente a linha alvo, mantendo as demais intactas', () => {
    const combos = gerarMatrizVariantes({
      nomeProduto: 'Top',
      cores: ['Coral', 'Preto'],
      tamanhos: ['M'],
      precoVendaBase: '79.90',
    })
    const alvo = combos[0]
    const atualizados = atualizarCombo(combos, alvo.id, { precoVenda: '89.90', estoqueInicial: 5 })

    expect(atualizados.find((c) => c.id === alvo.id)).toMatchObject({ precoVenda: '89.90', estoqueInicial: 5 })
    expect(atualizados.find((c) => c.id !== alvo.id)?.precoVenda).toBe('79.90')
  })
})

describe('TAMANHOS_SUGERIDOS', () => {
  it('cobre PP/P/M/G/GG', () => {
    expect(TAMANHOS_SUGERIDOS).toEqual(['PP', 'P', 'M', 'G', 'GG'])
  })
})
