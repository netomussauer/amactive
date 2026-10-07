import { afterEach, describe, expect, it } from 'vitest'
import { useToastStore } from './toast-store'

describe('useToastStore', () => {
  afterEach(() => {
    useToastStore.setState({ toasts: [] })
  })

  it('empilha um toast com id único', () => {
    useToastStore.getState().push('success', 'Produto cadastrado com sucesso!')
    useToastStore.getState().push('success', 'Outro toast')

    const { toasts } = useToastStore.getState()
    expect(toasts).toHaveLength(2)
    expect(toasts[0].id).not.toEqual(toasts[1].id)
  })

  it('não depende de crypto.randomUUID (indisponível fora de contexto seguro)', () => {
    // crypto.randomUUID só existe em HTTPS/localhost — qualquer acesso via
    // IP/hostname puro HTTP do laboratório (ex: http://192.168.1.213) não é
    // contexto seguro, então `crypto.randomUUID` é `undefined` aí. Simula
    // exatamente essa condição: se o push() voltar a chamá-lo, este teste
    // falha com o mesmo TypeError visto no navegador real (bug real,
    // 2026-10-07 — ver comentário em toast-store.ts).
    // `delete crypto.randomUUID` não funciona: o método vive no protótipo
    // (Crypto.prototype), não é propriedade própria da instância — delete
    // nela é um no-op que retorna `true` sem remover nada. Precisa
    // sombrear com uma propriedade própria `undefined`, que é exatamente
    // o que acontece de verdade num contexto não seguro.
    Object.defineProperty(crypto, 'randomUUID', { value: undefined, configurable: true })
    try {
      expect(() => useToastStore.getState().push('error', 'Falha')).not.toThrow()
      expect(useToastStore.getState().toasts).toHaveLength(1)
    } finally {
      // @ts-expect-error -- remove a propriedade própria, voltando a expor o método do protótipo.
      delete crypto.randomUUID
    }
  })

  it('remove um toast pelo id', () => {
    useToastStore.getState().push('info', 'Aviso')
    const [toast] = useToastStore.getState().toasts
    useToastStore.getState().dismiss(toast.id)

    expect(useToastStore.getState().toasts).toHaveLength(0)
  })
})
