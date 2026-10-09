import { afterEach, describe, expect, it, vi } from 'vitest'
import { useToastStore } from './toast-store'

describe('useToastStore', () => {
  afterEach(() => {
    useToastStore.setState({ toasts: [] })
    vi.useRealTimers()
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

  it('some sozinho depois de um tempo (bug real, 2026-10-10: nunca sumia, ficava empilhando)', () => {
    vi.useFakeTimers()
    useToastStore.getState().push('success', 'Adicionado ao carrinho')
    expect(useToastStore.getState().toasts).toHaveLength(1)

    vi.advanceTimersByTime(3999)
    expect(useToastStore.getState().toasts).toHaveLength(1)

    vi.advanceTimersByTime(1)
    expect(useToastStore.getState().toasts).toHaveLength(0)
  })

  it('toast de erro fica visível por mais tempo que sucesso/info antes de sumir sozinho', () => {
    vi.useFakeTimers()
    useToastStore.getState().push('error', 'Falha ao salvar')

    vi.advanceTimersByTime(4000)
    expect(useToastStore.getState().toasts).toHaveLength(1)

    vi.advanceTimersByTime(2000)
    expect(useToastStore.getState().toasts).toHaveLength(0)
  })

  it('fechar manualmente antes do timer não quebra quando o timer dispara depois', () => {
    vi.useFakeTimers()
    useToastStore.getState().push('info', 'Aviso')
    const [toast] = useToastStore.getState().toasts

    useToastStore.getState().dismiss(toast.id)
    expect(useToastStore.getState().toasts).toHaveLength(0)

    // O timer do push() ainda dispara mais tarde — dismiss() num id que já
    // não existe mais é um no-op, não deve re-adicionar nem lançar erro.
    expect(() => vi.advanceTimersByTime(4000)).not.toThrow()
    expect(useToastStore.getState().toasts).toHaveLength(0)
  })

  it('cada toast tem seu próprio timer independente', () => {
    vi.useFakeTimers()
    useToastStore.getState().push('success', 'Primeiro')
    vi.advanceTimersByTime(2000)
    useToastStore.getState().push('success', 'Segundo')

    // 2000ms depois do primeiro push (4000 total): só o primeiro já passou
    // da sua duração de 4000ms, o segundo ainda tem 2000ms pela frente.
    vi.advanceTimersByTime(2000)
    expect(useToastStore.getState().toasts.map((t) => t.message)).toEqual(['Segundo'])

    vi.advanceTimersByTime(2000)
    expect(useToastStore.getState().toasts).toHaveLength(0)
  })
})
