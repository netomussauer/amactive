import { useState } from 'react'
import { Input } from '@/shared/components/ui/Input'
import { Button } from '@/shared/components/ui/Button'
import { cn } from '@/shared/lib/utils'
import { TAMANHOS_SUGERIDOS } from '../lib/matriz-variantes'

type Props = {
  /** Tamanho atualmente selecionado (string livre — ver matriz-variantes.ts). */
  value: string
  onChange: (value: string) => void
  /** Prefixo para ids únicos dos elementos internos (input de tamanho personalizado). */
  idPrefix: string
  /** Rótulo acessível do grupo de botões. */
  ariaLabel: string
  invalid?: boolean
}

function normaliza(valor: string): string {
  return valor.trim().toLowerCase()
}

// Grade de botões clicáveis para selecionar o tamanho, substituindo o
// <input list="..."> (datalist nativo). O datalist do HTML5 não abre de
// forma confiável ao clicar — em boa parte dos navegadores Chromium a lista
// só aparece depois que o usuário digita algo, o que no formulário "Nova
// variante" parecia um combo quebrado (ver relato: clique no campo não
// mostrava as sugestões). `tamanho` continua sendo string livre no backend
// (docs/data-model.md decisão #8: varchar(10), PP/P/M/G/GG convivem com
// tamanhos numéricos como "38"), então a opção "Outro" garante que as
// sugestões pré-definidas nunca bloqueiam um tamanho fora da grade padrão.
export function SeletorTamanho({ value, onChange, idPrefix, ariaLabel, invalid }: Props) {
  const [mostrarCustom, setMostrarCustom] = useState(false)
  const [customInput, setCustomInput] = useState('')

  const ehSugestao = TAMANHOS_SUGERIDOS.some((tamanho) => normaliza(tamanho) === normaliza(value))
  // Valor atual fora da grade padrão (ex: editando uma variante já cadastrada
  // com tamanho "38") — exibido como um botão extra selecionado, igual ao
  // padrão de "cor personalizada" de PaletaDeCores.
  const customAtual = !ehSugestao && value.trim() !== '' ? value : null

  function selecionar(tamanho: string) {
    onChange(tamanho)
    setMostrarCustom(false)
  }

  function handleAdicionarCustom() {
    const tamanho = customInput.trim()
    if (!tamanho) return
    onChange(tamanho)
    setCustomInput('')
    setMostrarCustom(false)
  }

  return (
    <div id={idPrefix}>
      <div role="group" aria-label={ariaLabel} className="flex flex-wrap gap-2">
        {TAMANHOS_SUGERIDOS.map((tamanho) => {
          const selecionado = normaliza(tamanho) === normaliza(value)
          return (
            <button
              key={tamanho}
              type="button"
              aria-pressed={selecionado}
              onClick={() => selecionar(tamanho)}
              className={cn(
                'rounded-full border px-3 py-1.5 text-sm font-medium transition-colors',
                selecionado
                  ? 'border-primary bg-primary-subtle text-primary'
                  : 'border-border text-text-muted hover:bg-bg-subtle',
                invalid && !selecionado && 'border-danger',
              )}
            >
              {tamanho}
            </button>
          )
        })}

        {customAtual && (
          <button
            type="button"
            aria-pressed="true"
            title={`${customAtual} (personalizado) — clique para alterar`}
            onClick={() => setMostrarCustom(true)}
            className="rounded-full border border-primary bg-primary-subtle px-3 py-1.5 text-sm font-medium text-primary"
          >
            {customAtual}
          </button>
        )}

        <button
          type="button"
          aria-expanded={mostrarCustom}
          // Só referencia o id do input quando ele de fato existe no DOM
          // (renderizado condicionalmente) — evita aria-controls "órfão".
          aria-controls={mostrarCustom ? `${idPrefix}-custom-input` : undefined}
          onClick={() => setMostrarCustom((prev) => !prev)}
          className={cn(
            'rounded-full border border-dashed px-3 py-1.5 text-sm text-text-muted hover:bg-bg-subtle',
            invalid ? 'border-danger' : 'border-border',
          )}
        >
          Outro
        </button>
      </div>

      {mostrarCustom && (
        <div className="mt-2 flex gap-2">
          <Input
            id={`${idPrefix}-custom-input`}
            aria-label="Tamanho personalizado"
            placeholder="Ex: 38"
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
            Usar
          </Button>
        </div>
      )}
    </div>
  )
}
