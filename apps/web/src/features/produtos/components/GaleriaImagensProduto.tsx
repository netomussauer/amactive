import { useMemo } from 'react'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { Spinner } from '@/shared/components/ui/Spinner'
import { useImagensDoProduto } from '../hooks/useImagensDoProduto'
import { ImagemGaleriaCor } from './ImagemGaleriaCor'
import type { Imagem } from '../types/imagem.types'

type Props = {
  produtoId: string
  /** Cores das variantes ATIVAS do produto — só elas aceitam upload (ver docs/openapi.yaml, 422 se a cor não bater). */
  coresAtivas: string[]
}

// Seção "Galeria de imagens" da página de detalhe do produto, agrupada por
// cor. Também serve para adicionar imagens a produtos já existentes, não só
// recém-criados.
export function GaleriaImagensProduto({ produtoId, coresAtivas }: Props) {
  const { data, isLoading } = useImagensDoProduto(produtoId)

  const imagensPorCor = useMemo(() => {
    const mapa = new Map<string, Imagem[]>()
    for (const imagem of data?.data ?? []) {
      const lista = mapa.get(imagem.cor) ?? []
      lista.push(imagem)
      mapa.set(imagem.cor, lista)
    }
    return mapa
  }, [data])

  // Une as cores ativas (sempre exibidas, mesmo sem imagem ainda) com
  // eventuais cores que só existem porque a variante foi inativada depois
  // de já ter imagens — para não "sumir" com uma galeria já preenchida.
  const coresParaExibir = useMemo(() => {
    const todas = new Set([...coresAtivas, ...imagensPorCor.keys()])
    return Array.from(todas).sort((a, b) => a.localeCompare(b, 'pt-BR'))
  }, [coresAtivas, imagensPorCor])

  return (
    <Card>
      <CardHeader>
        <CardTitle>Galeria de imagens</CardTitle>
      </CardHeader>

      {isLoading ? (
        <Spinner label="Carregando galeria..." />
      ) : coresParaExibir.length === 0 ? (
        <EmptyState
          title="Nenhuma cor disponível"
          description="Cadastre ao menos uma variante (cor) antes de enviar imagens do produto."
        />
      ) : (
        <div className="space-y-4">
          {coresParaExibir.map((cor) => (
            <ImagemGaleriaCor key={cor} produtoId={produtoId} cor={cor} imagens={imagensPorCor.get(cor) ?? []} />
          ))}
        </div>
      )}
    </Card>
  )
}
