import { Component, Suspense, type ReactNode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { lazyWithReload } from './lazy-with-reload'

const CHAVE = 'amactive:chunk-reload-attempted'

class ErrorBoundaryDeTeste extends Component<
  { children: ReactNode },
  { erro: Error | null }
> {
  state = { erro: null as Error | null }
  static getDerivedStateFromError(erro: Error) {
    return { erro }
  }
  render() {
    if (this.state.erro) return <div>erro capturado: {this.state.erro.message}</div>
    return this.props.children
  }
}

describe('lazyWithReload', () => {
  let reloadSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    sessionStorage.clear()
    reloadSpy = vi.fn()
    // jsdom não implementa window.location.reload — substitui por um spy.
    Object.defineProperty(window, 'location', {
      value: { ...window.location, reload: reloadSpy },
      writable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('na primeira falha, recarrega a página uma vez e nunca deixa o erro subir', async () => {
    const Componente = lazyWithReload(() => Promise.reject(new Error('Failed to fetch dynamically imported module')))

    render(
      <ErrorBoundaryDeTeste>
        <Suspense fallback="carregando...">
          <Componente />
        </Suspense>
      </ErrorBoundaryDeTeste>,
    )

    await waitFor(() => expect(reloadSpy).toHaveBeenCalledTimes(1))
    expect(sessionStorage.getItem(CHAVE)).toBe('1')
    // A Promise da tentativa que falhou nunca resolve nem rejeita de volta
    // para o React — o fallback de carregamento continua na tela até o
    // reload de fato acontecer, sem "erro capturado" nenhum.
    expect(screen.queryByText(/erro capturado/i)).not.toBeInTheDocument()
  })

  it('se já tentou recarregar nesta aba, propaga o erro em vez de recarregar de novo (evita loop)', async () => {
    sessionStorage.setItem(CHAVE, '1')
    const Componente = lazyWithReload(() => Promise.reject(new Error('Failed to fetch dynamically imported module')))

    render(
      <ErrorBoundaryDeTeste>
        <Suspense fallback="carregando...">
          <Componente />
        </Suspense>
      </ErrorBoundaryDeTeste>,
    )

    expect(await screen.findByText(/erro capturado/i)).toBeInTheDocument()
    expect(reloadSpy).not.toHaveBeenCalled()
  })

  it('em caso de sucesso, limpa a flag de reload (libera uma nova tentativa em uma falha futura)', async () => {
    sessionStorage.setItem(CHAVE, '1')
    const Componente = lazyWithReload(() => Promise.resolve({ default: () => <div>ok</div> }))

    render(
      <Suspense fallback="carregando...">
        <Componente />
      </Suspense>,
    )

    expect(await screen.findByText('ok')).toBeInTheDocument()
    expect(sessionStorage.getItem(CHAVE)).toBeNull()
  })
})
