import { describe, expect, it } from 'vitest'
import { TAMANHO_MAXIMO_IMAGEM_BYTES, validarArquivoImagem } from './imagem-upload'

function makeFile({ type = 'image/jpeg', size = 1024 }: { type?: string; size?: number } = {}): File {
  const blob = new Blob([new Uint8Array(size)], { type })
  return new File([blob], 'foto.jpg', { type })
}

describe('validarArquivoImagem', () => {
  it('aceita jpeg, png e webp dentro do limite de tamanho', () => {
    expect(validarArquivoImagem(makeFile({ type: 'image/jpeg' }))).toBeNull()
    expect(validarArquivoImagem(makeFile({ type: 'image/png' }))).toBeNull()
    expect(validarArquivoImagem(makeFile({ type: 'image/webp' }))).toBeNull()
  })

  it('rejeita formatos não suportados', () => {
    expect(validarArquivoImagem(makeFile({ type: 'application/pdf' }))).toMatch(/formato inválido/i)
  })

  it('rejeita arquivo maior que 5MB', () => {
    expect(validarArquivoImagem(makeFile({ size: TAMANHO_MAXIMO_IMAGEM_BYTES + 1 }))).toMatch(/5mb/i)
  })

  it('aceita arquivo exatamente no limite de 5MB', () => {
    expect(validarArquivoImagem(makeFile({ size: TAMANHO_MAXIMO_IMAGEM_BYTES }))).toBeNull()
  })
})
