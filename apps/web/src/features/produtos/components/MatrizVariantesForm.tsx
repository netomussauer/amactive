import { useState } from 'react'
import { Plus, X } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { Badge } from '@/shared/components/ui/Badge'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { cn } from '@/shared/lib/utils'
import { PaletaDeCores } from './PaletaDeCores'
import {
  atualizarCombo,
  gerarMatrizVariantes,
  removerCombo,
  TAMANHOS_SUGERIDOS,
  type ComboVarianteMatriz,
} from '../lib/matriz-variantes'
import { useCriarVariantesEmLote, type ResultadoCombo } from '../hooks/useCriarVariantesEmLote'

const DECIMAL_PATTERN = /^\d+\.\d{2}$/

type Props = {
  produtoId: string
  nomeProduto: string
  onConcluido: () => void
  onPular: () => void
}

type StatusLinha = ResultadoCombo | 'pendente' | undefined

// Substitui o fluxo de "uma variante por vez" na criação de produto: o
// usuário define um conjunto de cores e um conjunto de tamanhos, revisa a
// prévia da matriz (cor × tamanho), remove combinações que não existem e
// ajusta preço por linha — ao confirmar, dispara um POST /variantes por
// combinação (não existe endpoint de lote no backend) e reporta o resultado
// de cada uma sem bloquear as que deram certo.
export function MatrizVariantesForm({ produtoId, nomeProduto, onConcluido, onPular }: Props) {
  const [cores, setCores] = useState<string[]>([])
  const [tamanhos, setTamanhos] = useState<string[]>([])
  const [tamanhoInput, setTamanhoInput] = useState('')
  const [precoVendaBase, setPrecoVendaBase] = useState('')
  const [precoCustoBase, setPrecoCustoBase] = useState('')
  const [estoqueInicialBase, setEstoqueInicialBase] = useState(0)
  const [erroGeracao, setErroGeracao] = useState<string | null>(null)

  const [combos, setCombos] = useState<ComboVarianteMatriz[]>([])
  const [statusPorId, setStatusPorId] = useState<Record<string, StatusLinha>>({})

  const { mutate: criarVariantes, isPending } = useCriarVariantesEmLote(produtoId)

  function toggleTamanhoSugerido(tamanho: string) {
    setTamanhos((prev) =>
      prev.some((t) => t.toLowerCase() === tamanho.toLowerCase())
        ? prev.filter((t) => t.toLowerCase() !== tamanho.toLowerCase())
        : [...prev, tamanho],
    )
  }

  function handleAddTamanhoCustom() {
    const valor = tamanhoInput.trim()
    if (!valor) return
    if (tamanhos.some((t) => t.toLowerCase() === valor.toLowerCase())) {
      setTamanhoInput('')
      return
    }
    setTamanhos((prev) => [...prev, valor])
    setTamanhoInput('')
  }

  function handleRemoveTamanho(tamanho: string) {
    setTamanhos((prev) => prev.filter((t) => t !== tamanho))
  }

  function handleGerarMatriz() {
    if (cores.length === 0 || tamanhos.length === 0) {
      setErroGeracao('Adicione ao menos uma cor e um tamanho para gerar a matriz.')
      return
    }
    if (!DECIMAL_PATTERN.test(precoVendaBase)) {
      setErroGeracao('Informe o preço de venda base no formato 129.90.')
      return
    }
    setErroGeracao(null)
    const novosCombos = gerarMatrizVariantes({
      nomeProduto,
      cores,
      tamanhos,
      precoVendaBase,
      precoCustoBase: precoCustoBase || undefined,
      estoqueInicialBase,
      combosExistentes: combos,
    })
    setCombos(novosCombos)
    setStatusPorId({})
  }

  function handleRemoverLinha(id: string) {
    setCombos((prev) => removerCombo(prev, id))
    setStatusPorId((prev) => {
      const resto = { ...prev }
      delete resto[id]
      return resto
    })
  }

  function handleAtualizarLinha(id: string, patch: Partial<Pick<ComboVarianteMatriz, 'sku' | 'precoVenda' | 'estoqueInicial'>>) {
    setCombos((prev) => atualizarCombo(prev, id, patch))
  }

  const combosPendentes = combos.filter((combo) => {
    const status = statusPorId[combo.id]
    return !status || status === 'pendente' || Boolean(status.erro)
  })

  function handleConfirmar() {
    const alvo = combosPendentes
    if (alvo.length === 0) return

    setStatusPorId((prev) => {
      const proximo = { ...prev }
      for (const combo of alvo) proximo[combo.id] = 'pendente'
      return proximo
    })

    criarVariantes(
      {
        combos: alvo,
        onProgresso: (resultado) => {
          setStatusPorId((prev) => ({ ...prev, [resultado.combo.id]: resultado }))
        },
      },
      {
        onSuccess: (resultados) => {
          if (resultados.every((r) => !r.erro)) onConcluido()
        },
      },
    )
  }

  const totalConcluidas = Object.values(statusPorId).filter((s) => s !== 'pendente' && s !== undefined).length
  const totalComErro = Object.values(statusPorId).filter((s) => s !== 'pendente' && s !== undefined && s.erro).length

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField
          label="Cores"
          htmlFor="matriz-cores"
          hint="Clique nos quadrados para selecionar uma ou mais cores, ou use 'Personalizada'"
        >
          <PaletaDeCores
            idPrefix="matriz-cores"
            ariaLabel="Cores"
            multiple
            value={cores}
            onChange={setCores}
          />
        </FormField>

        <FormField label="Tamanhos" htmlFor="matriz-tamanho-input" hint="Clique nas sugestões ou digite um tamanho numérico">
          <div className="mb-2 flex flex-wrap gap-2">
            {TAMANHOS_SUGERIDOS.map((tamanho) => {
              const ativo = tamanhos.some((t) => t.toLowerCase() === tamanho.toLowerCase())
              return (
                <button
                  key={tamanho}
                  type="button"
                  aria-pressed={ativo}
                  onClick={() => toggleTamanhoSugerido(tamanho)}
                  className={cn(
                    'rounded-full border px-3 py-1 text-xs font-medium transition-colors',
                    ativo ? 'border-primary bg-primary-subtle text-primary' : 'border-border text-text-muted hover:bg-bg-subtle',
                  )}
                >
                  {tamanho}
                </button>
              )
            })}
          </div>
          <div className="flex gap-2">
            <Input
              id="matriz-tamanho-input"
              placeholder="38"
              value={tamanhoInput}
              onChange={(event) => setTamanhoInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  handleAddTamanhoCustom()
                }
              }}
            />
            <Button type="button" variant="outline" size="icon" aria-label="Adicionar tamanho" onClick={handleAddTamanhoCustom}>
              <Plus className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
          {tamanhos.filter((t) => !TAMANHOS_SUGERIDOS.some((s) => s.toLowerCase() === t.toLowerCase())).length > 0 && (
            <ul className="mt-2 flex flex-wrap gap-2">
              {tamanhos
                .filter((t) => !TAMANHOS_SUGERIDOS.some((s) => s.toLowerCase() === t.toLowerCase()))
                .map((tamanho) => (
                  <li key={tamanho}>
                    <Badge tone="primary" className="gap-1.5">
                      {tamanho}
                      <button
                        type="button"
                        aria-label={`Remover tamanho ${tamanho}`}
                        onClick={() => handleRemoveTamanho(tamanho)}
                        className="rounded-full hover:opacity-70"
                      >
                        <X className="h-3 w-3" aria-hidden="true" />
                      </button>
                    </Badge>
                  </li>
                ))}
            </ul>
          )}
        </FormField>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <FormField label="Preço de venda base" htmlFor="matriz-preco-venda" required hint="Aplicado a todas as combinações, editável por linha">
          <Input
            id="matriz-preco-venda"
            placeholder="129.90"
            value={precoVendaBase}
            onChange={(event) => setPrecoVendaBase(event.target.value)}
          />
        </FormField>
        <FormField label="Preço de custo base" htmlFor="matriz-preco-custo" hint="Opcional">
          <Input
            id="matriz-preco-custo"
            placeholder="60.00"
            value={precoCustoBase}
            onChange={(event) => setPrecoCustoBase(event.target.value)}
          />
        </FormField>
        <FormField label="Estoque inicial (todas)" htmlFor="matriz-estoque-inicial">
          <Input
            id="matriz-estoque-inicial"
            type="number"
            min={0}
            value={estoqueInicialBase}
            onChange={(event) => setEstoqueInicialBase(Number(event.target.value) || 0)}
          />
        </FormField>
      </div>

      {erroGeracao && (
        <p role="alert" className="text-sm text-danger">
          {erroGeracao}
        </p>
      )}

      <Button type="button" variant="outline" onClick={handleGerarMatriz}>
        {combos.length > 0 ? 'Atualizar matriz' : 'Gerar matriz de variantes'}
      </Button>

      {combos.length > 0 && (
        <div className="space-y-3">
          <Table aria-label="Prévia da matriz de variantes">
            <TableHead>
              <TableRow>
                <TableHeadCell>Cor</TableHeadCell>
                <TableHeadCell>Tamanho</TableHeadCell>
                <TableHeadCell>SKU</TableHeadCell>
                <TableHeadCell>Preço de venda</TableHeadCell>
                <TableHeadCell>Estoque inicial</TableHeadCell>
                <TableHeadCell>Status</TableHeadCell>
                <TableHeadCell className="text-right">Ações</TableHeadCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {combos.map((combo) => {
                const status = statusPorId[combo.id]
                const concluidaComSucesso = status !== undefined && status !== 'pendente' && !status.erro
                const rotulo = `${combo.cor} ${combo.tamanho}`
                return (
                  <TableRow key={combo.id}>
                    <TableCell>{combo.cor}</TableCell>
                    <TableCell>{combo.tamanho}</TableCell>
                    <TableCell>
                      <Input
                        aria-label={`SKU da combinação ${rotulo}`}
                        className="font-mono text-xs"
                        value={combo.sku}
                        disabled={concluidaComSucesso}
                        onChange={(event) => handleAtualizarLinha(combo.id, { sku: event.target.value })}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        aria-label={`Preço de venda da combinação ${rotulo}`}
                        value={combo.precoVenda}
                        disabled={concluidaComSucesso}
                        onChange={(event) => handleAtualizarLinha(combo.id, { precoVenda: event.target.value })}
                      />
                    </TableCell>
                    <TableCell>
                      <Input
                        aria-label={`Estoque inicial da combinação ${rotulo}`}
                        type="number"
                        min={0}
                        value={combo.estoqueInicial}
                        disabled={concluidaComSucesso}
                        onChange={(event) =>
                          handleAtualizarLinha(combo.id, { estoqueInicial: Number(event.target.value) || 0 })
                        }
                      />
                    </TableCell>
                    <TableCell>
                      {!status && <Badge tone="neutral">Pronta</Badge>}
                      {status === 'pendente' && <Badge tone="pendente">Enviando...</Badge>}
                      {status !== undefined && status !== 'pendente' && !status.erro && <Badge tone="ok">Criada</Badge>}
                      {status !== undefined && status !== 'pendente' && status.erro && (
                        <div>
                          <Badge tone="critico">Erro</Badge>
                          <p role="alert" className="mt-1 text-xs text-danger">
                            {status.erro}
                          </p>
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {!concluidaComSucesso && (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          aria-label={`Remover combinação ${rotulo}`}
                          onClick={() => handleRemoverLinha(combo.id)}
                        >
                          <X className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>

          {totalConcluidas > 0 && (
            <p className="text-sm text-text-muted">
              {totalConcluidas - totalComErro} de {combos.length} criada(s)
              {totalComErro > 0 && ` · ${totalComErro} com erro (ajuste e clique em "Criar variantes" novamente)`}
            </p>
          )}

          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              isLoading={isPending}
              aria-busy={isPending}
              disabled={combosPendentes.length === 0}
              onClick={handleConfirmar}
            >
              {isPending ? 'Criando variantes...' : `Criar ${combosPendentes.length} variante(s)`}
            </Button>
            {totalConcluidas > 0 && totalComErro === 0 && (
              <Button type="button" variant="outline" onClick={onConcluido}>
                Ver produto
              </Button>
            )}
          </div>
        </div>
      )}

      <Button type="button" variant="ghost" onClick={onPular}>
        Pular esta etapa e ver o produto
      </Button>
    </div>
  )
}
