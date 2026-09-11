import { useRef, useState } from 'react'
import { ChevronDown, ChevronUp, Star, Trash2, Upload } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Badge } from '@/shared/components/ui/Badge'
import { getMediaUrl } from '@/shared/lib/api-client'
import { getErrorMessage } from '@/shared/lib/get-error-message'
import { cn } from '@/shared/lib/utils'
import { validarArquivoImagem } from '../lib/imagem-upload'
import { useUploadImagem } from '../hooks/useUploadImagem'
import { useDefinirImagemPrincipal } from '../hooks/useDefinirImagemPrincipal'
import { useAtualizarOrdemImagem } from '../hooks/useAtualizarOrdemImagem'
import { useRemoverImagem } from '../hooks/useRemoverImagem'
import type { Imagem } from '../types/imagem.types'

type Props = {
  produtoId: string
  cor: string
  imagens: Imagem[]
}

// Galeria de imagens de UMA cor: miniaturas + ações (principal, reordenar,
// remover) e upload (drag-and-drop ou seletor de arquivo). A `cor` precisa
// bater exatamente com uma cor de variante ativa do produto — o backend
// responde 422 com uma mensagem clara quando não bate, exibida abaixo do
// dropzone (ver docs/openapi.yaml POST /produtos/{produtoId}/imagens).
export function ImagemGaleriaCor({ produtoId, cor, imagens }: Props) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [erroArquivo, setErroArquivo] = useState<string | null>(null)

  const { mutate: upload, isPending: isUploading, error: erroUpload } = useUploadImagem(produtoId)
  const { mutate: definirPrincipal } = useDefinirImagemPrincipal(produtoId)
  const { mutate: atualizarOrdem } = useAtualizarOrdemImagem(produtoId)
  const { mutate: remover } = useRemoverImagem(produtoId)

  const imagensOrdenadas = [...imagens].sort((a, b) => a.ordem - b.ordem)

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return
    for (const arquivo of Array.from(files)) {
      const erro = validarArquivoImagem(arquivo)
      if (erro) {
        setErroArquivo(erro)
        continue
      }
      setErroArquivo(null)
      upload({ cor, arquivo })
    }
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault()
    setIsDragOver(false)
    handleFiles(event.dataTransfer.files)
  }

  function handleMover(index: number, direcao: -1 | 1) {
    const alvoIndex = index + direcao
    if (alvoIndex < 0 || alvoIndex >= imagensOrdenadas.length) return
    const atual = imagensOrdenadas[index]
    const vizinho = imagensOrdenadas[alvoIndex]
    atualizarOrdem({ imagemId: atual.id, payload: { ordem: vizinho.ordem } })
    atualizarOrdem({ imagemId: vizinho.id, payload: { ordem: atual.ordem } })
  }

  function handleRemover(imagem: Imagem) {
    if (window.confirm(`Remover esta imagem da cor ${cor}?`)) {
      remover(imagem.id)
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-border p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-sans text-sm font-semibold text-text">{cor}</h3>
        <Badge tone="neutral">{imagensOrdenadas.length} imagem(ns)</Badge>
      </div>

      {imagensOrdenadas.length === 0 ? (
        <p className="text-sm text-text-muted">Nenhuma imagem cadastrada para esta cor ainda.</p>
      ) : (
        <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
          {imagensOrdenadas.map((imagem, index) => (
            <li key={imagem.id} className="relative overflow-hidden rounded-md border border-border">
              <img
                src={getMediaUrl(imagem.url)}
                alt={`Imagem da cor ${cor}`}
                className="h-28 w-full object-cover"
              />
              {imagem.principal && (
                <span
                  className="absolute left-1.5 top-1.5 inline-flex items-center gap-1 rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-white"
                  aria-label="Imagem principal desta cor"
                >
                  <Star className="h-3 w-3 fill-current" aria-hidden="true" />
                  Principal
                </span>
              )}
              <div className="flex items-center justify-between gap-1 bg-bg-subtle p-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={`Mover imagem ${index + 1} da cor ${cor} para cima`}
                  disabled={index === 0}
                  onClick={() => handleMover(index, -1)}
                >
                  <ChevronUp className="h-4 w-4" aria-hidden="true" />
                </Button>
                {!imagem.principal && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Definir imagem ${index + 1} da cor ${cor} como principal`}
                    onClick={() => definirPrincipal(imagem.id)}
                  >
                    <Star className="h-4 w-4" aria-hidden="true" />
                  </Button>
                )}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={`Mover imagem ${index + 1} da cor ${cor} para baixo`}
                  disabled={index === imagensOrdenadas.length - 1}
                  onClick={() => handleMover(index, 1)}
                >
                  <ChevronDown className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={`Remover imagem ${index + 1} da cor ${cor}`}
                  onClick={() => handleRemover(imagem)}
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div
        onDrop={handleDrop}
        onDragOver={(event) => {
          event.preventDefault()
          setIsDragOver(true)
        }}
        onDragLeave={() => setIsDragOver(false)}
        className={cn(
          'rounded-md border border-dashed border-border p-4 text-center transition-colors',
          isDragOver && 'border-primary bg-primary-subtle',
        )}
      >
        <button
          type="button"
          aria-label={`Enviar imagem para a cor ${cor}`}
          aria-busy={isUploading}
          onClick={() => inputRef.current?.click()}
          className={cn(
            'flex w-full flex-col items-center justify-center gap-1 text-xs text-text-muted',
            isDragOver && 'text-primary',
          )}
        >
          <Upload className="h-4 w-4" aria-hidden="true" />
          <span>{isUploading ? 'Enviando...' : `Arraste uma imagem ou clique para enviar (cor: ${cor})`}</span>
        </button>
        <input
          ref={inputRef}
          type="file"
          aria-label={`Enviar imagem para a cor ${cor}`}
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="sr-only"
          onChange={(event) => {
            handleFiles(event.target.files)
            event.target.value = ''
          }}
        />
      </div>

      {erroArquivo && (
        <p role="alert" className="text-xs text-danger">
          {erroArquivo}
        </p>
      )}
      {erroUpload && (
        <p role="alert" className="text-xs text-danger">
          {getErrorMessage(erroUpload)}
        </p>
      )}
    </div>
  )
}
