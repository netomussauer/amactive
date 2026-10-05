import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Minus, Plus } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Skeleton } from '@/shared/components/ui/Skeleton'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { PrecoPromocional } from '@/shared/components/ui/PrecoPromocional'
import { getMediaUrl } from '@/shared/lib/api-client'
import { formatCurrencyBRL } from '@/shared/lib/format'
import { toast } from '@/shared/lib/toast'
import { ProdutoCard } from '../components/ProdutoCard'
import { useProdutoLoja, useRelacionadosLoja } from '../hooks/useLojaQueries'
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
  // Começa na primeira cor que já tem foto; se nenhuma tiver, na primeira cor.
  const corInicial =
    coresDisponiveis.find((c) => produto.imagens.some((i) => i.cor === c)) ?? coresDisponiveis[0] ?? ''
  const [cor, setCor] = useState(corInicial)
  const variantesDaCor = useMemo(
    () => produto.variantes.filter((v) => v.cor === cor),
    [produto, cor],
  )
  const [varianteId, setVarianteId] = useState<string | null>(null)
  const [quantidade, setQuantidade] = useState(1)

  const varianteSelecionada =
    variantesDaCor.find((v) => v.id === varianteId) ?? variantesDaCor.find((v) => v.disponivel > 0) ?? variantesDaCor[0]

  // Só as fotos DESTA cor. Sem foto para a cor escolhida, a vitrine não mostra a
  // foto de outra cor: exibe um aviso no lugar (ver o bloco de imagem abaixo).
  const galeria = produto.imagens.filter((i) => i.cor === cor)
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
    <div className="flex flex-col gap-10 pb-24 md:pb-0">
      <nav aria-label="Caminho" className="text-sm text-text-muted">
        <ol className="flex flex-wrap items-center gap-2">
          <li>
            <Link to="/" className="hover:text-text">
              Coleção
            </Link>
          </li>
          {produto.categoria && (
            <>
              <li aria-hidden="true">/</li>
              <li>
                <Link to={`/?categoria=${produto.categoria.id}`} className="hover:text-text">
                  {produto.categoria.nome}
                </Link>
              </li>
            </>
          )}
          <li aria-hidden="true">/</li>
          <li aria-current="page" className="text-text">
            {produto.nome}
          </li>
        </ol>
      </nav>

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
            <div className="flex h-full items-center justify-center px-6 text-center text-sm text-text-muted">
              {produto.imagens.length > 0 ? `Foto de ${cor} em breve` : 'Sem imagem'}
            </div>
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

      <ProdutosRelacionados produtoAtualId={produto.id} categoriaId={produto.categoria?.id} />

      {/* Compra sempre à mão no celular: o botão principal pode estar longe do olhar ao rolar. */}
      <div className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-between gap-3 border-t border-border bg-bg p-3 shadow-lg md:hidden">
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-xs text-text-muted">
            {varianteSelecionada ? `${varianteSelecionada.tamanho} · ${varianteSelecionada.cor}` : ''}
          </span>
          <span className="font-semibold text-primary">
            {varianteSelecionada ? formatCurrencyBRL(varianteSelecionada.preco_unitario) : ''}
          </span>
        </div>
        <Button size="lg" disabled={esgotado} onClick={adicionarAoCarrinho}>
          {esgotado ? 'Esgotado' : 'Adicionar'}
        </Button>
      </div>
    </div>
  )
}

function ProdutosRelacionados({
  produtoAtualId,
  categoriaId,
}: {
  produtoAtualId: string
  categoriaId: string | undefined
}) {
  const relacionados = useRelacionadosLoja(categoriaId)
  const itens = (relacionados.data?.data ?? []).filter((p) => p.id !== produtoAtualId).slice(0, 4)
  if (itens.length === 0) return null

  return (
    <section aria-labelledby="relacionados-titulo" className="flex flex-col gap-4">
      <h2 id="relacionados-titulo" className="font-sans text-xl font-semibold text-text">
        Você também pode gostar
      </h2>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {itens.map((produto) => (
          <ProdutoCard key={produto.id} produto={produto} />
        ))}
      </div>
    </section>
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
