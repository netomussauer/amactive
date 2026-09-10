import { useState } from 'react'
import { Search, Plus } from 'lucide-react'
import { Input } from '@/shared/components/ui/Input'
import { Button } from '@/shared/components/ui/Button'
import { Badge } from '@/shared/components/ui/Badge'
import { Spinner } from '@/shared/components/ui/Spinner'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { cn } from '@/shared/lib/utils'
import { formatCurrencyBRL } from '@/shared/lib/format'
import { useProdutoPorSku, useProdutos, useVariantesDoProduto } from '@/features/produtos'
import { useCarrinhoStore } from '../store/carrinho.store'
import type { CarrinhoItem } from '../types/pedido.types'

type Modo = 'sku' | 'nome'

function SkuResult() {
  const [sku, setSku] = useState('')
  const skuDebounced = useDebounce(sku)
  const { data: resultado, isFetching } = useProdutoPorSku(skuDebounced, true)
  const addItem = useCarrinhoStore((state) => state.addItem)

  const semEstoque = resultado ? resultado.variante.quantidade_estoque <= 0 : false

  function handleAdd() {
    if (!resultado || semEstoque) return
    const item: CarrinhoItem = {
      varianteId: resultado.variante.id,
      sku: resultado.variante.sku,
      produtoNome: resultado.produtoNome,
      tamanho: resultado.variante.tamanho,
      cor: resultado.variante.cor,
      precoUnitario: resultado.variante.preco_venda,
      quantidade: 1,
      descontoItem: '0.00',
      estoqueDisponivel: resultado.variante.quantidade_estoque,
    }
    addItem(item)
    setSku('')
  }

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" aria-hidden="true" />
        <Input
          aria-label="Buscar por SKU"
          placeholder="Digite ou escaneie o SKU e pressione Enter"
          className="pl-9"
          value={sku}
          onChange={(event) => setSku(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && resultado && !semEstoque) {
              event.preventDefault()
              handleAdd()
            }
          }}
          autoFocus
        />
      </div>

      {isFetching && <p className="text-sm text-text-muted">Buscando...</p>}

      {!isFetching && skuDebounced && !resultado && (
        <p role="alert" className="text-sm text-danger">
          Nenhum produto encontrado para o SKU "{skuDebounced}".
        </p>
      )}

      {resultado && (
        <div className="flex items-center justify-between gap-3 rounded-md border border-border p-3">
          <div>
            <p className="font-medium text-text">
              {resultado.produtoNome} — {resultado.variante.tamanho}/{resultado.variante.cor}
            </p>
            <p className="text-sm text-text-muted">
              SKU {resultado.variante.sku} · {formatCurrencyBRL(resultado.variante.preco_venda)}
            </p>
            {semEstoque ? (
              <Badge tone="critico" className="mt-1">
                Sem estoque disponível
              </Badge>
            ) : (
              <Badge tone="ok" className="mt-1">
                {resultado.variante.quantidade_estoque} em estoque
              </Badge>
            )}
          </div>
          <Button type="button" onClick={handleAdd} disabled={semEstoque} size="sm">
            <Plus className="h-4 w-4" aria-hidden="true" />
            Adicionar
          </Button>
        </div>
      )}
    </div>
  )
}

function VariantesDoProduto({ produtoId, produtoNome }: { produtoId: string; produtoNome: string }) {
  const { data, isLoading } = useVariantesDoProduto(produtoId)
  const addItem = useCarrinhoStore((state) => state.addItem)

  if (isLoading) return <Spinner label="Carregando variantes..." />

  const variantesAtivas = data?.data.filter((v) => v.ativo) ?? []

  if (variantesAtivas.length === 0) {
    return <p className="p-3 text-sm text-text-muted">Nenhuma variante ativa cadastrada para este produto.</p>
  }

  return (
    <ul className="divide-y divide-border">
      {variantesAtivas.map((variante) => {
        const semEstoque = variante.quantidade_estoque <= 0
        return (
          <li key={variante.id} className="flex items-center justify-between gap-3 py-2">
            <div>
              <p className="text-sm font-medium text-text">
                {variante.tamanho}/{variante.cor} · {formatCurrencyBRL(variante.preco_venda)}
              </p>
              <p className="text-xs text-text-muted">
                SKU {variante.sku} · {semEstoque ? 'sem estoque' : `${variante.quantidade_estoque} em estoque`}
              </p>
            </div>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={semEstoque}
              onClick={() =>
                addItem({
                  varianteId: variante.id,
                  sku: variante.sku,
                  produtoNome,
                  tamanho: variante.tamanho,
                  cor: variante.cor,
                  precoUnitario: variante.preco_venda,
                  quantidade: 1,
                  descontoItem: '0.00',
                  estoqueDisponivel: variante.quantidade_estoque,
                })
              }
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Adicionar
            </Button>
          </li>
        )
      })}
    </ul>
  )
}

function NomeResult() {
  const [nome, setNome] = useState('')
  const [produtoExpandidoId, setProdutoExpandidoId] = useState<string | null>(null)
  const nomeDebounced = useDebounce(nome)
  const { data, isFetching } = useProdutos({ busca: nomeDebounced || undefined, ativo: true, per_page: 10 })

  return (
    <div className="space-y-3">
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" aria-hidden="true" />
        <Input
          aria-label="Buscar produto por nome"
          placeholder="Digite o nome do produto..."
          className="pl-9"
          value={nome}
          onChange={(event) => setNome(event.target.value)}
          autoFocus
        />
      </div>

      {isFetching && <p className="text-sm text-text-muted">Buscando...</p>}

      {!isFetching && nomeDebounced && (data?.data.length ?? 0) === 0 && (
        <p role="alert" className="text-sm text-danger">
          Nenhum produto encontrado para "{nomeDebounced}".
        </p>
      )}

      <ul className="space-y-2">
        {data?.data.map((produto) => (
          <li key={produto.id} className="rounded-md border border-border">
            <button
              type="button"
              className="flex w-full items-center justify-between p-3 text-left text-sm font-medium text-text hover:bg-bg-subtle"
              onClick={() => setProdutoExpandidoId((current) => (current === produto.id ? null : produto.id))}
              aria-expanded={produtoExpandidoId === produto.id}
            >
              {produto.nome}
              <span className="text-xs text-text-muted">{produtoExpandidoId === produto.id ? 'Ocultar' : 'Ver variantes'}</span>
            </button>
            {produtoExpandidoId === produto.id && (
              <div className="border-t border-border px-3 pb-2">
                <VariantesDoProduto produtoId={produto.id} produtoNome={produto.nome} />
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}

// Painel de busca do PDV: alterna entre busca por SKU (match exato) e por
// nome do produto (navega pelas variantes).
export function PdvBuscaProduto() {
  const [modo, setModo] = useState<Modo>('sku')

  return (
    <div>
      <div role="tablist" aria-label="Modo de busca" className="mb-3 flex gap-1 rounded-md border border-border bg-bg p-1">
        <button
          type="button"
          role="tab"
          aria-selected={modo === 'sku'}
          className={cn('flex-1 rounded px-3 py-1.5 text-sm font-medium', modo === 'sku' ? 'bg-primary text-white' : 'text-text-muted')}
          onClick={() => setModo('sku')}
        >
          Por SKU
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={modo === 'nome'}
          className={cn('flex-1 rounded px-3 py-1.5 text-sm font-medium', modo === 'nome' ? 'bg-primary text-white' : 'text-text-muted')}
          onClick={() => setModo('nome')}
        >
          Por nome
        </button>
      </div>

      {modo === 'sku' ? <SkuResult /> : <NomeResult />}
    </div>
  )
}
