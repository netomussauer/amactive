import { Link, Outlet } from 'react-router-dom'
import { MessageCircle, ShoppingBag } from 'lucide-react'
import { WHATSAPP_LOJA } from '../config'
import { useCarrinhoStore, quantidadeDeItens } from '../store/carrinho.store'

export function LojaLayout() {
  const quantidade = useCarrinhoStore((estado) => quantidadeDeItens(estado.itens))

  return (
    <div className="flex min-h-screen flex-col bg-bg text-text">
      <header className="sticky top-0 z-10 border-b border-border bg-bg/95 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2" aria-label="AMACTIVE — início da loja">
            <img src="/brand/amactive-icon-primary.png" alt="" className="h-7 w-auto" />
            <span className="font-sans text-lg font-bold tracking-tight text-primary">AMACTIVE</span>
          </Link>
          <Link
            to="/carrinho"
            className="relative inline-flex h-10 items-center gap-2 rounded-md px-3 text-sm font-medium hover:bg-bg-subtle"
          >
            <ShoppingBag className="h-5 w-5" aria-hidden="true" />
            <span>Carrinho</span>
            {quantidade > 0 && (
              <span
                className="ml-1 inline-flex min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-semibold text-white"
                aria-label={`${quantidade} item(ns) no carrinho`}
              >
                {quantidade}
              </span>
            )}
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <Outlet />
      </main>

      <footer className="border-t border-border bg-bg-subtle">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-8 text-sm text-text-muted md:flex-row md:items-center md:justify-between">
          <div className="flex flex-col gap-1">
            <img src="/brand/amactive-logo-primary.png" alt="AMACTIVE" className="h-8 w-auto self-start" />
            <p>Activewear para te acompanhar dentro e fora do treino.</p>
          </div>
          {WHATSAPP_LOJA ? (
            <a
              href={`https://wa.me/${WHATSAPP_LOJA}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex w-fit items-center gap-2 font-medium text-primary underline-offset-4 hover:underline"
            >
              <MessageCircle className="h-4 w-4" aria-hidden="true" />
              Fale conosco pelo WhatsApp
            </a>
          ) : null}
        </div>
        <p className="border-t border-border py-4 text-center text-xs text-text-muted">
          © AMACTIVE · Pedidos confirmados e pagamento combinados pelo WhatsApp da loja.
        </p>
      </footer>
    </div>
  )
}
