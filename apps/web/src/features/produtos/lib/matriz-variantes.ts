// Lógica pura de geração da matriz cor × tamanho usada no cadastro de
// variantes de um produto (ver docs/frontend-architecture.md — não existe
// endpoint de criação em lote no backend, então o frontend monta a matriz e
// orquestra uma chamada POST /produtos/{id}/variantes por combinação, ver
// hooks/useCriarVariantesEmLote.ts).
//
// Mantido como funções puras (sem React) para ser 100% testável sem mocks.

// Tamanhos sugeridos por padrão no formulário — não é um enum fechado no
// backend (docs/data-model.md decisão #8: `tamanho` é varchar(10) porque
// tamanhos numéricos como "38"/"40" coexistem com PP/P/M/G/GG), mas cobre o
// caso comum de moda fitness por letra.
export const TAMANHOS_SUGERIDOS = ['PP', 'P', 'M', 'G', 'GG'] as const

export type ComboVarianteMatriz = {
  /** Chave estável cor+tamanho (normalizada), usada como key de lista e para merge ao regenerar. */
  id: string
  cor: string
  tamanho: string
  sku: string
  precoVenda: string
  precoCusto?: string
  estoqueInicial: number
}

/**
 * Convenção de SKU adotada para a matriz (nenhuma outra convenção estava
 * documentada em docs/ — definida aqui e usada de forma determinística):
 *
 *   <3 primeiras letras do nome do produto>-<COR sem espaços/acentos>-<TAMANHO>
 *
 * Ex: "Legging Fitness Alta Compressão" + cor "Coral" + tamanho "M"
 *     => "LEG-CORAL-M"
 *
 * Sempre maiúsculo, sem acentos/pontuação. O SKU gerado é apenas uma
 * sugestão pré-preenchida e editável por linha no formulário — se colidir
 * com um SKU já existente, o backend responde 422 e a combinação
 * correspondente é reportada como falha sem bloquear as demais.
 */
export function gerarSkuVariante(nomeProduto: string, cor: string, tamanho: string): string {
  const primeiraPalavra = nomeProduto.trim().split(/\s+/)[0] ?? ''
  const prefixo = normalizarToken(primeiraPalavra).slice(0, 3) || 'PRD'
  const corToken = normalizarToken(cor) || 'COR'
  const tamanhoToken = normalizarToken(tamanho) || 'UN'
  return `${prefixo}-${corToken}-${tamanhoToken}`
}

function normalizarToken(valor: string): string {
  return valor
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '') // remove acentos/diacríticos
    .replace(/[^a-zA-Z0-9]+/g, '') // remove espaços/pontuação
    .toUpperCase()
}

function comboId(cor: string, tamanho: string): string {
  return `${cor.trim().toLowerCase()}__${tamanho.trim().toLowerCase()}`
}

// Remove valores vazios/duplicados (case-insensitive), preservando a
// primeira grafia informada pelo usuário.
function dedupNaoVazios(valores: string[]): string[] {
  const vistos = new Set<string>()
  const resultado: string[] = []
  for (const valor of valores) {
    const limpo = valor.trim()
    if (!limpo) continue
    const chave = limpo.toLowerCase()
    if (vistos.has(chave)) continue
    vistos.add(chave)
    resultado.push(limpo)
  }
  return resultado
}

type GerarMatrizParams = {
  nomeProduto: string
  cores: string[]
  tamanhos: string[]
  precoVendaBase: string
  precoCustoBase?: string
  estoqueInicialBase?: number
  /** Combos já existentes (ex: ao regenerar após adicionar uma cor) — preserva overrides de preço/SKU/estoque já editados manualmente. */
  combosExistentes?: ComboVarianteMatriz[]
}

// Gera o produto cartesiano cor × tamanho. Combinações repetidas em `cores`
// ou `tamanhos` (mesmo com grafia/caixa diferente) são ignoradas. Se um
// combo já existir em `combosExistentes` (mesma cor+tamanho), ele é
// reaproveitado como está — permite ao usuário adicionar uma cor nova sem
// perder os ajustes de preço já feitos nas demais linhas.
export function gerarMatrizVariantes(params: GerarMatrizParams): ComboVarianteMatriz[] {
  const cores = dedupNaoVazios(params.cores)
  const tamanhos = dedupNaoVazios(params.tamanhos)
  const existentesPorId = new Map((params.combosExistentes ?? []).map((combo) => [combo.id, combo]))

  const combos: ComboVarianteMatriz[] = []
  for (const cor of cores) {
    for (const tamanho of tamanhos) {
      const id = comboId(cor, tamanho)
      const existente = existentesPorId.get(id)
      combos.push(
        existente ?? {
          id,
          cor,
          tamanho,
          sku: gerarSkuVariante(params.nomeProduto, cor, tamanho),
          precoVenda: params.precoVendaBase,
          precoCusto: params.precoCustoBase,
          estoqueInicial: params.estoqueInicialBase ?? 0,
        },
      )
    }
  }
  return combos
}

// Remove uma combinação da matriz (ex: "nem toda cor tem todo tamanho").
export function removerCombo(combos: ComboVarianteMatriz[], id: string): ComboVarianteMatriz[] {
  return combos.filter((combo) => combo.id !== id)
}

// Atualiza um campo editável de uma linha específica (override individual de
// preço/SKU/estoque) sem afetar as demais combinações.
export function atualizarCombo(
  combos: ComboVarianteMatriz[],
  id: string,
  patch: Partial<Pick<ComboVarianteMatriz, 'sku' | 'precoVenda' | 'precoCusto' | 'estoqueInicial'>>,
): ComboVarianteMatriz[] {
  return combos.map((combo) => (combo.id === id ? { ...combo, ...patch } : combo))
}
