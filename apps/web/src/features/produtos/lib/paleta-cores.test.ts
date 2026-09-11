import { describe, expect, it } from 'vitest'
import { isCorClara, PALETA_CORES_PADRAO } from './paleta-cores'

describe('paleta-cores', () => {
  it('expõe uma lista de cores com nome e hex válido', () => {
    expect(PALETA_CORES_PADRAO.length).toBeGreaterThan(0)
    for (const cor of PALETA_CORES_PADRAO) {
      expect(cor.nome.length).toBeGreaterThan(0)
      expect(cor.hex).toMatch(/^#[0-9a-fA-F]{6}$/)
    }
  })

  it('não tem nomes de cor duplicados (case-insensitive)', () => {
    const nomes = PALETA_CORES_PADRAO.map((cor) => cor.nome.toLowerCase())
    expect(new Set(nomes).size).toBe(nomes.length)
  })

  describe('isCorClara', () => {
    it('identifica branco como cor clara', () => {
      expect(isCorClara('#ffffff')).toBe(true)
    })

    it('identifica preto como cor escura', () => {
      expect(isCorClara('#0a0a0a')).toBe(false)
    })

    it('identifica o coral de assinatura como cor escura o suficiente para ícone branco', () => {
      expect(isCorClara('#ff6b4a')).toBe(false)
    })
  })
})
