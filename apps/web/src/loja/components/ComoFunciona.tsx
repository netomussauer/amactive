import { MessageCircle, ShoppingBag, Wallet } from 'lucide-react'

// Explica o fluxo real da compra na vitrine (ver docs/vitrine-online.md §2).
// Não promete prazos nem condições comerciais: só descreve o que acontece.
const PASSOS = [
  {
    icone: ShoppingBag,
    titulo: 'Escolha suas peças',
    texto: 'Selecione cor e tamanho e adicione ao carrinho. As peças ficam reservadas para você.',
  },
  {
    icone: MessageCircle,
    titulo: 'Envie o pedido pelo WhatsApp',
    texto: 'Ao finalizar, você recebe um resumo pronto para enviar à loja.',
  },
  {
    icone: Wallet,
    titulo: 'Combine pagamento e entrega',
    texto: 'A equipe confirma seu pedido e combina a forma de pagamento com você pelo WhatsApp.',
  },
]

export function ComoFunciona() {
  return (
    <section aria-labelledby="como-funciona-titulo" className="flex flex-col gap-6">
      <h2 id="como-funciona-titulo" className="font-sans text-2xl font-semibold text-text">
        Como funciona a compra
      </h2>
      <ol className="grid gap-4 md:grid-cols-3">
        {PASSOS.map(({ icone: Icone, titulo, texto }, indice) => (
          <li key={titulo} className="flex flex-col gap-3 rounded-lg border border-border p-5">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700">
                {indice + 1}
              </span>
              <Icone className="h-5 w-5 text-primary" aria-hidden="true" />
            </div>
            <p className="font-medium text-text">{titulo}</p>
            <p className="text-sm text-text-muted">{texto}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
