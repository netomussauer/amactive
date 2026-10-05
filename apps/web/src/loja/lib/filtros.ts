// Opções de filtro e ordenação da vitrine. Os filtros vivem na URL
// (?categoria=…&cor=…&tamanho=…&preco=…&ordem=…), então uma listagem filtrada
// pode ser compartilhada e o botão "voltar" do navegador funciona.

export type FaixaPrecoId = 'todas' | 'ate-100' | '100-150' | 'acima-150'

export type FaixaPreco = {
  id: FaixaPrecoId
  label: string
  /** Valores enviados à API no formato decimal fixo (ex.: "100.00"). */
  min?: string
  max?: string
}

export const FAIXAS_PRECO: readonly FaixaPreco[] = [
  { id: 'todas', label: 'Todos os preços' },
  { id: 'ate-100', label: 'Até R$ 100', max: '100.00' },
  { id: '100-150', label: 'R$ 100 a R$ 150', min: '100.00', max: '150.00' },
  { id: 'acima-150', label: 'Acima de R$ 150', min: '150.00' },
]

export type OrdemListagem = 'nome' | 'preco_asc' | 'preco_desc' | 'desconto'

export const ORDENACOES: readonly { value: OrdemListagem; label: string }[] = [
  { value: 'nome', label: 'Nome (A–Z)' },
  { value: 'preco_asc', label: 'Menor preço' },
  { value: 'preco_desc', label: 'Maior preço' },
  { value: 'desconto', label: 'Maior desconto' },
]

/** Faixa de preço a partir do valor da URL. Valor desconhecido vira "todos". */
export function faixaPorId(valor: string | null): FaixaPreco {
  return FAIXAS_PRECO.find((f) => f.id === valor) ?? FAIXAS_PRECO[0]
}

/** Ordenação a partir do valor da URL. Valor desconhecido vira "nome". */
export function ordemValida(valor: string | null): OrdemListagem {
  return ORDENACOES.find((o) => o.value === valor)?.value ?? 'nome'
}
