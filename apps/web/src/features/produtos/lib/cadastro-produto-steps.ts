import type { StepperStep } from '@/shared/components/ui/Stepper'

// Passos do fluxo de cadastro de produto, compartilhados entre
// ProdutoNovoPage (passos 1 e 2) e ProdutoDetalhePage (passo 3, exibido
// apenas quando o usuário chega ali vindo do fluxo de criação — ver
// `state.fromCadastro` passado na navegação de ProdutoNovoPage).
export const CADASTRO_PRODUTO_STEPS: StepperStep[] = [
  { id: 'dados', label: 'Dados do produto' },
  { id: 'variantes', label: 'Variantes (cor × tamanho)' },
  { id: 'imagens', label: 'Imagens' },
]
