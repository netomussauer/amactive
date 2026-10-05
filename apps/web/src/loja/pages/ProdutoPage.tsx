import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Minus, Plus } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Skeleton } from '@/shared/components/ui/Skeleton'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { PrecoPromocional } from '@/shared/components/ui/PrecoPromocional'
import { getMediaUrl } from '@/shared/lib/api-client'
import { toast } from '@/shared/lib/toast'
import { useProdutoLoja } from '../hooks/useLojaQueries'
import { useCarrinhoStore, LIMITE_QUANTIDADE_POR_ITEM } from '../store/carrinho.store'
import type { ProdutoDetalheLoja, VarianteLoja } from '../schemas/loja.schema'

export function ProdutoPage() {
  const { produtoId = '' } = useParams()
  const produto = useProdutoLoja(produtoId)

  if (produto.isPending) {
    return (
      <div className="grid gap-6 md:grid-cols-2" aria-busy="true">
        <Skeleton className="aspect-[3/4] w-full" />
        <div className="flex flex-col gap-3">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-6 w-1/3" />
        </div>
      </div>
    )
  }

  if (produto.isError || !produto.data) {
    return (
      <EmptyState
        title="Produto indisponível"
        description="Ele pode ter saído de linha. Veja os demais produtos da coleção."
        action={
          <Link to="/" className="text-sm font-medium text-primary underline">
            Voltar para a coleção
          </Link>
        }
      />
    )
  }

  return <DetalheProduto produto={produto.data} />
}

function DetalheProduto({ produto }: { produto: ProdutoDetalheLoja }) {
  const coresDisponiveis = useMemo(() => [...new Set(produto.variantes.map((v) => v.cor))], [produto])
  const [cor, setCor] = useState(coresDisponiveis[0] ?? '')
  const variantesDaCor = useMemo(
    () => produto.variantes.filter((v) => v.cor === cor),
    [produto, cor],
  )
  const [varianteId, setVarianteId] = useState<string | null>(null)
  const [quantidade, setQuantidade] = useState(1)

  const varianteSelecionada =
    variantesDaCor.find((v) => v.id === varianteId) ?? variantesDaCor.find((v) => v.disponivel > 0) ?? variantesDaCor[0]

  const imagensDaCor = produto.imagens.filter((i) => i.cor === cor)
  const galeria = imagensDaCor.length > 0 ? imagensDaCor : produto.imagens.slice(0, 1)
  const [indiceImagem, setIndiceImagem] = useState(0)
  const imagemAtual = galeria[indiceImagem] ?? galeria[0]

  const adicionar = useCarrinhoStore((estado) => estado.adicionar)
  const esgotado = !varianteSelecionada || varianteSelecionada.disponivel <= 0
  const limiteQuantidade = varianteSelecionada
    ? Math.min(varianteSelecionada.disponivel, LIMITE_QUANTIDADE_POR_ITEM)
    : 0
  const quantidadeEscolhida = Math.min(quantidade, Math.max(limiteQuantidade, 1))

  function escolherCor(novaCor: string) {
    setCor(novaCor)
    setVarianteId(null)
    setIndiceImagem(0)
    setQuantidade(1)
  }

  function adicionarAoCarrinho() {
    if (!varianteSelecionada) return
    adicionar(
      {
        varianteId: varianteSelecionada.id,
        produtoId: produto.id,
        produtoNome: produto.nome,
        cor: varianteSelecionada.cor,
        tamanho: varianteSelecionada.tamanho,
        sku: varianteSelecionada.sku,
        precoUnitario: varianteSelecionada.preco_unitario,
        precoCheio: varianteSelecionada.preco_cheio,
        disponivel: varianteSelecionada.disponivel,
      },
      quantidadeEscolhida,
    )
    toast.success('Adicionado ao carrinho')
  }

  return (
    <div className="grid gap-8 md:grid-cols-2">
      <div className="flex flex-col gap-3">
        <div className="aspect-[3/4] overflow-hidden rounded-lg bg-bg-subtle">
          {imagemAtual ? (
            <img
              src={getMediaUrl(imagemAtual.url)}
              alt={`${produto.nome} — ${cor}`}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-sm text-text-muted">Sem imagem</div>
          )}
        </div>
        {galeria.length > 1 && (
          <div className="flex gap-2 overflow-x-auto" role="group" aria-label="Imagens do produto">
            {galeria.map((imagem, i) => (
              <button
                key={imagem.url}
                type="button"
                onClick={() => setIndiceImagem(i)}
                aria-pressed={i === indiceImagem}
                aria-label={`Ver imagem ${i + 1}`}
                className={`h-16 w-12 shrink-0 overflow-hidden rounded border ${i === indiceImagem ? 'border-primary' : 'border-border'}`}
              >
                <img src={getMediaUrl(imagem.url)} alt="" className="h-full w-full object-cover" />
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <p className="text-sm text-text-muted">{produto.categoria?.nome ?? produto.marca}</p>
          <h1 className="font-sans text-2xl font-semibold text-text">{produto.nome}</h1>
          {varianteSelecionada && (
            <PrecoPromocional
              className="text-lg"
              precoOriginal={varianteSelecionada.preco_cheio}
              precoPromocional={
                varianteSelecionada.preco_unitario !== varianteSelecionada.preco_cheio
                  ? varianteSelecionada.preco_unitario
                  : null
              }
              descontoPercentual={produto.desconto_percentual}
            />
          )}
          {produto.descricao && <p className="text-sm text-text-muted">{produto.descricao}</p>}
        </div>

        {coresDisponiveis.length > 1 && (
          <fieldset className="flex flex-col gap-2">
            <legend className="text-sm font-medium">Cor: <span className="font-normal">{cor}</span></legend>
            <div className="flex flex-wrap gap-2">
              {coresDisponiveis.map((c) => (
                <Button
                  key={c}
                  size="sm"
                  variant={c === cor ? 'primary' : 'outline'}
                  aria-pressed={c === cor}
                  onClick={() => escolherCor(c)}
                >
                  {c}
                </Button>
              ))}
            </div>
          </fieldset>
        )}

        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium">Tamanho</legend>
          <div className="flex flex-wrap gap-2">
            {variantesDaCor.map((variante) => (
              <TamanhoOpcao
                key={variante.id}
                variante={variante}
                selecionada={variante.id === varianteSelecionada?.id}
                onSelecionar={() => {
                  setVarianteId(variante.id)
                  setQuantidade(1)
                }}
              />
            ))}
          </div>
        </fieldset>

        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <span className="text-sm font-medium">Quantidade</span>
            <div className="flex items-center rounded-md border border-border">
              <Button
                variant="ghost"
                size="icon"
                aria-label="Diminuir quantidade"
                disabled={esgotado || quantidadeEscolhida <= 1}
                onClick={() => setQuantidade(Math.max(quantidadeEscolhida - 1, 1))}
              >
                <Minus className="h-4 w-4" aria-hidden="true" />
              </Button>
              <span className="w-10 text-center text-sm font-medium" aria-live="polite">
                {esgotado ? 0 : quantidadeEscolhida}
              </span>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Aumentar quantidade"
                disabled={esgotado || quantidadeEscolhida >= limiteQuantidade}
                onClick={() => setQuantidade(Math.min(quantidadeEscolhida + 1, limiteQuantidade))}
              >
                <Plus className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
            {varianteSelecionada && !esgotado && varianteSelecionada.disponivel <= 3 && (
              <span className="text-xs text-status-baixo">Últimas {varianteSelecionada.disponivel} unidade(s)</span>
            )}
          </div>

          <Button size="lg" disabled={esgotado} onClick={adicionarAoCarrinho}>
            {esgotado ? 'Esgotado' : 'Adicionar ao carrinho'}
          </Button>
          <p className="text-xs text-text-muted">
            As peças ficam reservadas somente após você enviar o pedido.
          </p>
        </div>
      </div>
    </div>
  )
}

function TamanhoOpcao({
  variante,
  selecionada,
  onSelecionar,
}: {
  variante: VarianteLoja
  selecionada: boolean
  onSelecionar: () => void
}) {
  const esgotada = variante.disponivel <= 0
  return (
    <Button
      size="sm"
      variant={selecionada ? 'primary' : 'outline'}
      aria-pressed={selecionada}
      onClick={onSelecionar}
      className={esgotada ? 'line-through opacity-60' : undefined}
      aria-label={esgotada ? `${variante.tamanho} (esgotado)` : variante.tamanho}
    >
      {variante.tamanho}
    </Button>
  )
}
