import { useMemo, useState } from 'react'
import { Minus, Plus, Trash2, Search } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { Badge } from '@/shared/components/ui/Badge'
import { formatCurrencyBRL, formatPercent } from '@/shared/lib/format'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { useClientes } from '@/features/clientes'
import { useCarrinhoStore } from '../store/carrinho.store'

export function calcularSubtotalItem(precoUnitario: string, quantidade: number, descontoItem: string): number {
  return Number(precoUnitario) * quantidade - Number(descontoItem)
}

export function PdvCarrinho() {
  const itens = useCarrinhoStore((state) => state.itens)
  const clienteId = useCarrinhoStore((state) => state.clienteId)
  const setClienteId = useCarrinhoStore((state) => state.setClienteId)
  const updateQuantidade = useCarrinhoStore((state) => state.updateQuantidade)
  const removeItem = useCarrinhoStore((state) => state.removeItem)

  const [buscaCliente, setBuscaCliente] = useState('')
  const [clienteNome, setClienteNome] = useState<string | null>(null)
  const buscaClienteDebounced = useDebounce(buscaCliente)
  const { data: clientes } = useClientes({ busca: buscaClienteDebounced || undefined, per_page: 10 })

  const total = useMemo(
    () => itens.reduce((acc, item) => acc + calcularSubtotalItem(item.precoUnitario, item.quantidade, item.descontoItem), 0),
    [itens],
  )

  if (itens.length === 0) {
    return (
      <EmptyState
        title="Carrinho vazio"
        description="Busque um produto por SKU ou nome para começar a montar a venda."
      />
    )
  }

  return (
    <div className="space-y-4">
      <ul className="divide-y divide-border rounded-md border border-border">
        {itens.map((item) => (
          <li key={item.varianteId} className="flex flex-wrap items-center justify-between gap-3 p-3">
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium text-text">
                {item.produtoNome} — {item.tamanho}/{item.cor}
              </p>
              {item.precoPromocional ? (
                <>
                  <p className="flex flex-wrap items-center gap-1 text-xs text-text-muted">
                    SKU {item.sku} ·{' '}
                    <span className="line-through">{formatCurrencyBRL(item.precoUnitario)}</span>{' '}
                    <span className="font-medium text-primary">{formatCurrencyBRL(item.precoPromocional)}</span> cada
                  </p>
                  <Badge tone="primary" className="mt-1">
                    Promoção -{formatPercent(item.descontoPercentual)}
                  </Badge>
                </>
              ) : (
                <p className="text-xs text-text-muted">
                  SKU {item.sku} · {formatCurrencyBRL(item.precoUnitario)} cada
                </p>
              )}
            </div>

            <div className="flex items-center gap-1">
              <Button
                type="button"
                variant="outline"
                size="icon"
                aria-label={`Diminuir quantidade de ${item.sku}`}
                onClick={() => updateQuantidade(item.varianteId, item.quantidade - 1)}
                disabled={item.quantidade <= 1}
              >
                <Minus className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
              <span className="w-8 text-center text-sm font-medium" aria-live="polite">
                {item.quantidade}
              </span>
              <Button
                type="button"
                variant="outline"
                size="icon"
                aria-label={`Aumentar quantidade de ${item.sku}`}
                onClick={() => updateQuantidade(item.varianteId, item.quantidade + 1)}
                disabled={item.quantidade >= item.estoqueDisponivel}
              >
                <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </div>

            <p className="w-24 text-right font-medium text-text">
              {formatCurrencyBRL(calcularSubtotalItem(item.precoUnitario, item.quantidade, item.descontoItem))}
            </p>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label={`Remover ${item.sku} do carrinho`}
              onClick={() => removeItem(item.varianteId)}
            >
              <Trash2 className="h-4 w-4 text-danger" aria-hidden="true" />
            </Button>
          </li>
        ))}
      </ul>

      <div className="flex items-center justify-between rounded-md bg-bg-subtle p-3">
        <span className="font-medium text-text">Subtotal</span>
        <span className="font-sans text-lg font-bold text-text">{formatCurrencyBRL(total)}</span>
      </div>

      <FormField label="Cliente (opcional)" htmlFor="busca-cliente" hint="Vincule um cliente cadastrado à venda">
        <div className="relative mb-2">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" aria-hidden="true" />
          <Input
            id="busca-cliente"
            className="pl-9"
            placeholder="Buscar cliente por nome, e-mail ou CPF..."
            value={buscaCliente}
            onChange={(event) => setBuscaCliente(event.target.value)}
          />
        </div>
        {buscaClienteDebounced && (
          <ul className="max-h-40 overflow-y-auto rounded-md border border-border">
            {clientes?.data.length === 0 && <li className="p-2 text-sm text-text-muted">Nenhum cliente encontrado.</li>}
            {clientes?.data.map((cliente) => (
              <li key={cliente.id}>
                <button
                  type="button"
                  className="w-full px-3 py-2 text-left text-sm hover:bg-bg-subtle"
                  onClick={() => {
                    setClienteId(cliente.id)
                    setClienteNome(cliente.nome)
                    setBuscaCliente('')
                  }}
                >
                  {cliente.nome}
                </button>
              </li>
            ))}
          </ul>
        )}
        {clienteId && (
          <div className="mt-2 flex items-center justify-between rounded-md border border-primary bg-primary-subtle px-3 py-2 text-sm">
            <span>{clienteNome ?? 'Cliente vinculado'}</span>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                setClienteId(null)
                setClienteNome(null)
              }}
            >
              Remover
            </Button>
          </div>
        )}
      </FormField>
    </div>
  )
}
