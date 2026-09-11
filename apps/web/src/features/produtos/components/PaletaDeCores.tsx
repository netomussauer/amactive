import { useState } from 'react'
import { Check, Plus } from 'lucide-react'
import { Input } from '@/shared/components/ui/Input'
import { Button } from '@/shared/components/ui/Button'
import { cn } from '@/shared/lib/utils'
import { PALETA_CORES_PADRAO, isCorClara } from '../lib/paleta-cores'

type Props = {
  /** Cores atualmente selecionadas (nomes). Em modo `single`, no máximo 1 item. */
  value: string[]
  onChange: (value: string[]) => void
  /** `true` (padrão): seleção múltipla (matriz de variantes). `false`: seleção única (variante avulsa). */
  multiple?: boolean
  /** Prefixo para ids únicos dos elementos internos (input de cor personalizada). */
  idPrefix: string
  /** Rótulo acessível do grupo de swatches (ex: "Cores" ou "Cor"). */
  ariaLabel: string
  className?: string
}

function normaliza(valor: string): string {
  return valor.trim().toLowerCase()
}

// Grade de quadrados coloridos clicáveis para selecionar cor(es), usada como
// alternativa ao texto livre em MatrizVariantesForm (multi-seleção) e
// VarianteForm (seleção única). `cor` continua sendo string livre no backend
// (docs/data-model.md decisão #13) — a opção "Personalizada" garante que a
// paleta pré-definida nunca bloqueia o cadastro de uma cor real da marca.
export function PaletaDeCores({ value, onChange, multiple = true, idPrefix, ariaLabel, className }: Props) {
  const [mostrarCustom, setMostrarCustom] = useState(false)
  const [customInput, setCustomInput] = useState('')

  // Cores selecionadas que não fazem parte da paleta pré-definida (ex:
  // adicionadas via "Personalizada", ou já vindas de uma variante existente
  // com uma cor fora da lista) — exibidas como swatches extras removíveis.
  const coresExtras = value.filter(
    (cor) => !PALETA_CORES_PADRAO.some((padrao) => normaliza(padrao.nome) === normaliza(cor)),
  )

  function isSelecionada(cor: string): boolean {
    return value.some((v) => normaliza(v) === normaliza(cor))
  }

  function handleToggle(cor: string) {
    if (isSelecionada(cor)) {
      onChange(value.filter((v) => normaliza(v) !== normaliza(cor)))
      return
    }
    onChange(multiple ? [...value, cor] : [cor])
  }

  function handleAdicionarCustom() {
    const nome = customInput.trim()
    if (!nome) return
    setCustomInput('')
    setMostrarCustom(false)
    if (isSelecionada(nome)) return
    onChange(multiple ? [...value, nome] : [nome])
  }

  return (
    <div id={idPrefix} className={className}>
      <div role="group" aria-label={ariaLabel} className="grid grid-cols-4 gap-2 sm:grid-cols-5 md:grid-cols-6">
        {PALETA_CORES_PADRAO.map((cor) => {
          const selecionada = isSelecionada(cor.nome)
          return (
            <button
              key={cor.nome}
              type="button"
              aria-pressed={selecionada}
              title={cor.nome}
              onClick={() => handleToggle(cor.nome)}
              className={cn(
                'flex flex-col items-center gap-1 rounded-md border p-1.5 text-center transition-colors',
                selecionada ? 'border-primary bg-primary-subtle' : 'border-border hover:bg-bg-subtle',
              )}
            >
              <span
                aria-hidden="true"
                className="flex h-7 w-7 items-center justify-center rounded border border-border"
                style={{ backgroundColor: cor.hex }}
              >
                {selecionada && (
                  <Check
                    className={cn('h-4 w-4', isCorClara(cor.hex) ? 'text-graphite-900' : 'text-white')}
                    aria-hidden="true"
                  />
                )}
              </span>
              <span className="text-[11px] leading-tight text-text-muted">{cor.nome}</span>
            </button>
          )
        })}

        {coresExtras.map((cor) => (
          <button
            key={cor}
            type="button"
            aria-pressed="true"
            title={`${cor} (personalizada) — clique para remover`}
            onClick={() => handleToggle(cor)}
            className="flex flex-col items-center gap-1 rounded-md border border-primary bg-primary-subtle p-1.5 text-center"
          >
            <span
              aria-hidden="true"
              className="flex h-7 w-7 items-center justify-center rounded border border-dashed border-primary text-primary"
            >
              <Check className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="text-[11px] leading-tight text-text-muted">{cor}</span>
          </button>
        ))}

        <button
          type="button"
          aria-expanded={mostrarCustom}
          // Só referencia o id do input quando ele de fato existe no DOM
          // (renderizado condicionalmente) — evita aria-controls "órfão".
          aria-controls={mostrarCustom ? `${idPrefix}-cor-custom-input` : undefined}
          onClick={() => setMostrarCustom((prev) => !prev)}
          className="flex flex-col items-center gap-1 rounded-md border border-dashed border-border p-1.5 text-center hover:bg-bg-subtle"
        >
          <span
            aria-hidden="true"
            className="flex h-7 w-7 items-center justify-center rounded border border-dashed border-border text-text-muted"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
          </span>
          <span className="text-[11px] leading-tight text-text-muted">Personalizada</span>
        </button>
      </div>

      {mostrarCustom && (
        <div className="mt-2 flex gap-2">
          <Input
            id={`${idPrefix}-cor-custom-input`}
            aria-label="Nome da cor personalizada"
            placeholder="Ex: Terracota"
            value={customInput}
            onChange={(event) => setCustomInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                handleAdicionarCustom()
              }
            }}
          />
          <Button type="button" variant="outline" onClick={handleAdicionarCustom}>
            Adicionar
          </Button>
        </div>
      )}
    </div>
  )
}
