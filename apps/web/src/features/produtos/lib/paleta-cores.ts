// Paleta gráfica de cores comuns de moda fitness feminina, usada apenas como
// UX de seleção nos formulários de variante (matriz e variante avulsa).
// `cor` continua sendo string livre no backend — deliberadamente sem
// tabela/enum de cores (docs/data-model.md decisão #13, mesma decisão usada
// em `produto_imagem.cor`) — por isso esta lista NUNCA pode ser a única forma
// de informar a cor; ver "Personalizada" em PaletaDeCores.tsx.
export type CorPaleta = {
  nome: string
  hex: string
}

export const PALETA_CORES_PADRAO: CorPaleta[] = [
  { nome: 'Preto', hex: '#0a0a0a' },
  { nome: 'Branco', hex: '#ffffff' },
  { nome: 'Cinza', hex: '#9ca3af' },
  { nome: 'Cinza Mescla', hex: '#b3aeb0' },
  { nome: 'Off White', hex: '#f2ede1' },
  { nome: 'Nude', hex: '#e3c1a5' },
  { nome: 'Bege', hex: '#d8c3a5' },
  { nome: 'Rosa', hex: '#f472b6' },
  { nome: 'Rosa Bebê', hex: '#fbcfe8' },
  { nome: 'Coral', hex: '#ff6b4a' }, // = --color-coral-500 (styles/tokens.css) — cor de assinatura AMACTIVE
  { nome: 'Vermelho', hex: '#dc2626' },
  { nome: 'Vinho', hex: '#6d1f2b' },
  { nome: 'Roxo', hex: '#7c3aed' },
  { nome: 'Lilás', hex: '#c4b5fd' },
  { nome: 'Azul', hex: '#2563eb' },
  { nome: 'Azul Marinho', hex: '#1e3a5f' },
  { nome: 'Verde', hex: '#16a34a' },
  { nome: 'Verde Militar', hex: '#4d5d3a' },
  { nome: 'Amarelo', hex: '#facc15' },
]

// Decide se o ícone de seleção sobre o quadrado de cor deve ser escuro ou
// claro, para manter contraste legível independente da cor escolhida
// (luminância perceptual aproximada — não é a fórmula de contraste completa
// da WCAG, só o suficiente para este uso decorativo pontual).
export function isCorClara(hex: string): boolean {
  const valor = hex.replace('#', '')
  const r = parseInt(valor.slice(0, 2), 16)
  const g = parseInt(valor.slice(2, 4), 16)
  const b = parseInt(valor.slice(4, 6), 16)
  if ([r, g, b].some((canal) => Number.isNaN(canal))) return true
  const luminancia = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminancia > 0.6
}
