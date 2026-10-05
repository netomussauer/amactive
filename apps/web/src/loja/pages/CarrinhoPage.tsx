import { Link, useNavigate } from 'react-router-dom'
import { Minus, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { formatCurrencyBRL } from '@/shared/lib/format'
import { useCarrinhoStore, totalEmCentavos, LIMITE_QUANTIDADE_POR_ITEM } from '../store/carrinho.store'
import type { ItemCarrinho } from '../store/carrinho.store'

export function CarrinhoPage() {
  const itens = useCarrinhoStore((estado) => estado.itens)
  const alterarQuantidade = useCarrinhoStore((estado) => estado.alterarQuantidade)
  const remover = useCarrinhoStore((estado) => estado.remover)
  const navigate = useNavigate()

  if (itens.length === 0) {
    return (
      <EmptyState
        title="Seu carrinho está vazio"
        description="Escolha as peças da coleção e elas aparecem aqui."
        action={
          <Link to="/" className="text-sm font-medium text-primary underline">
            Ver a coleção
          </Link>
        }
      />
    )
  }

  const total = totalEmCentavos(itens)

  return (
    <div className="grid gap-8 md:grid-cols-[1fr_320px]">
      <section aria-labelledby="titulo-carrinho" className="flex flex-col gap-4">
        <h1 id="titulo-carrinho" className="font-sans text-2xl font-semibold text-text">
          Carrinho
        </h1>
        <ul className="flex flex-col divide-y divide-border rounded-lg border border-border">
          {itens.map((item) => (
            <LinhaCarrinho
              key={item.varianteId}
              item={item}
              onAlterarQuantidade={(q) => alterarQuantidade(item.varianteId, q)}
              onRemover={() => remover(item.varianteId)}
            />
          ))}
        </ul>
        <Link to="/" className="text-sm font-medium text-primary underline">
          Continuar comprando
        </Link>
      </section>

      <aside aria-label="Resumo do pedido" className="flex h-fit flex-col gap-4 rounded-lg border border-border p-5">
        <div className="flex items-center justify-between text-base font-semibold">
          <span>Total</span>
          <span>{formatCurrencyBRL(total / 100)}</span>
        </div>
        <p className="text-xs text-text-muted">
          Os preços finais são conferidos no envio do pedido. As peças só são reservadas após o envio, e o
          pagamento é combinado pelo WhatsApp da loja.
        </p>
        <Button size="lg" onClick={() => navigate('/finalizar')}>
          Finalizar pedido
        </Button>
      </aside>
    </div>
  )
}

function LinhaCarrinho({
  item,
  onAlterarQuantidade,
  onRemover,
}: {
  item: ItemCarrinho
  onAlterarQuantidade: (quantidade: number) => void
  onRemover: () => void
}) {
  const limite = Math.min(item.disponivel, LIMITE_QUANTIDADE_POR_ITEM)
  const subtotal = Math.round(Number(item.precoUnitario) * 100) * item.quantidade

  return (
    <li className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col">
        <span className="font-medium text-text">{item.produtoNome}</span>
        <span className="text-sm text-text-muted">
          {item.cor} · {item.tamanho} · {formatCurrencyBRL(item.precoUnitario)} cada
        </span>
        {item.quantidade >= limite && limite < LIMITE_QUANTIDADE_POR_ITEM && (
          <span className="text-xs text-status-baixo">Quantidade máxima disponível</span>
        )}
      </div>
      <div className="flex items-center justify-between gap-4 sm:justify-end">
        <div className="flex items-center rounded-md border border-border">
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Diminuir quantidade de ${item.produtoNome}`}
            disabled={item.quantidade <= 1}
            onClick={() => onAlterarQuantidade(item.quantidade - 1)}
          >
            <Minus className="h-4 w-4" aria-hidden="true" />
          </Button>
          <span className="w-10 text-center text-sm font-medium" aria-live="polite">
            {item.quantidade}
          </span>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Aumentar quantidade de ${item.produtoNome}`}
            disabled={item.quantidade >= limite}
            onClick={() => onAlterarQuantidade(item.quantidade + 1)}
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        <span className="w-24 text-right font-semibold">{formatCurrencyBRL(subtotal / 100)}</span>
        <Button
          variant="ghost"
          size="icon"
          aria-label={`Remover ${item.produtoNome} do carrinho`}
          onClick={onRemover}
        >
          <Trash2 className="h-4 w-4 text-danger" aria-hidden="true" />
        </Button>
      </div>
    </li>
  )
}
