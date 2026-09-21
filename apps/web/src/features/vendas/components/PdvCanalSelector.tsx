import { cn } from '@/shared/lib/utils'
import { useCarrinhoStore } from '../store/carrinho.store'
import { ORIGEM_CANAL_OPTIONS } from '../lib/canal'

// Segmented control (radio group nativo) do canal de origem da venda.
// O canal vive no store do carrinho; PdvPagamentoForm reage à troca
// (reseta pagamentos e número do pedido externo).
export function PdvCanalSelector() {
  const origemCanal = useCarrinhoStore((state) => state.origemCanal)
  const setOrigemCanal = useCarrinhoStore((state) => state.setOrigemCanal)

  return (
    <fieldset>
      <legend className="mb-1.5 text-sm font-medium text-text">Canal da venda</legend>
      <div className="inline-flex rounded-md border border-border bg-bg p-1">
        {ORIGEM_CANAL_OPTIONS.map((option) => {
          const selecionado = option.value === origemCanal
          return (
            <label
              key={option.value}
              className={cn(
                'relative cursor-pointer rounded px-4 py-1.5 text-sm font-medium transition-colors',
                'focus-within:ring-2 focus-within:ring-primary',
                selecionado ? 'bg-primary text-white' : 'text-text hover:bg-bg-subtle',
              )}
            >
              <input
                type="radio"
                name="origem-canal"
                value={option.value}
                checked={selecionado}
                onChange={() => setOrigemCanal(option.value)}
                className="sr-only"
              />
              {option.label}
            </label>
          )
        })}
      </div>
    </fieldset>
  )
}
