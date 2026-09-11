import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe, toHaveNoViolations } from 'jest-axe'
import { MatrizVariantesForm } from './MatrizVariantesForm'
import type { ComboVarianteMatriz } from '../lib/matriz-variantes'

expect.extend(toHaveNoViolations)

type MutateOptions = { onSuccess?: (resultados: unknown[]) => void }
type MutateVariables = {
  combos: ComboVarianteMatriz[]
  onProgresso?: (resultado: { combo: ComboVarianteMatriz; variante?: unknown; erro?: string }, indice: number, total: number) => void
}

let comportamento: 'sucesso' | 'falha-parcial' = 'sucesso'
const mutateMock = vi.fn((variables: MutateVariables, options?: MutateOptions) => {
  const resultados = variables.combos.map((combo, index) => {
    const erro = comportamento === 'falha-parcial' && combo.cor === 'Preto' ? 'SKU já cadastrado' : undefined
    const resultado = erro ? { combo, erro } : { combo, variante: { id: `v-${index}` } }
    variables.onProgresso?.(resultado, index + 1, variables.combos.length)
    return resultado
  })
  options?.onSuccess?.(resultados)
})

vi.mock('../hooks/useCriarVariantesEmLote', () => ({
  useCriarVariantesEmLote: () => ({ mutate: mutateMock, isPending: false }),
}))

async function gerarMatrizComDuasCores(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: 'Coral' }))
  await user.click(screen.getByRole('button', { name: 'Preto' }))

  await user.click(screen.getByRole('button', { name: 'M' }))

  await user.type(screen.getByLabelText(/preço de venda base/i), '129.90')
  await user.click(screen.getByRole('button', { name: /gerar matriz de variantes/i }))
}

describe('MatrizVariantesForm', () => {
  beforeEach(() => {
    comportamento = 'sucesso'
    mutateMock.mockClear()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('gera a prévia da matriz cor × tamanho com SKU determinístico', async () => {
    const user = userEvent.setup()
    render(
      <MatrizVariantesForm produtoId="produto-1" nomeProduto="Legging Fitness" onConcluido={vi.fn()} onPular={vi.fn()} />,
    )

    await gerarMatrizComDuasCores(user)

    expect(screen.getByLabelText(/sku da combinação coral m/i)).toHaveValue('LEG-CORAL-M')
    expect(screen.getByLabelText(/sku da combinação preto m/i)).toHaveValue('LEG-PRETO-M')
  })

  it('remove uma combinação da prévia sem afetar as demais', async () => {
    const user = userEvent.setup()
    render(
      <MatrizVariantesForm produtoId="produto-1" nomeProduto="Legging Fitness" onConcluido={vi.fn()} onPular={vi.fn()} />,
    )

    await gerarMatrizComDuasCores(user)
    await user.click(screen.getByRole('button', { name: /remover combinação preto m/i }))

    expect(screen.queryByLabelText(/sku da combinação preto m/i)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/sku da combinação coral m/i)).toBeInTheDocument()
  })

  it('dispara uma criação por combinação e avança quando todas têm sucesso', async () => {
    const user = userEvent.setup()
    const onConcluido = vi.fn()
    render(
      <MatrizVariantesForm produtoId="produto-1" nomeProduto="Legging Fitness" onConcluido={onConcluido} onPular={vi.fn()} />,
    )

    await gerarMatrizComDuasCores(user)
    await user.click(screen.getByRole('button', { name: /criar 2 variante/i }))

    expect(mutateMock).toHaveBeenCalledTimes(1)
    expect(mutateMock.mock.calls[0][0].combos).toHaveLength(2)
    expect(onConcluido).toHaveBeenCalledTimes(1)
  })

  it('reporta qual combinação falhou sem bloquear as que deram certo', async () => {
    comportamento = 'falha-parcial'
    const user = userEvent.setup()
    const onConcluido = vi.fn()
    render(
      <MatrizVariantesForm produtoId="produto-1" nomeProduto="Legging Fitness" onConcluido={onConcluido} onPular={vi.fn()} />,
    )

    await gerarMatrizComDuasCores(user)
    await user.click(screen.getByRole('button', { name: /criar 2 variante/i }))

    expect(await screen.findByText('SKU já cadastrado')).toBeInTheDocument()
    expect(screen.getAllByText('Criada')).toHaveLength(1)
    expect(screen.getAllByText('Erro')).toHaveLength(1)
    // não avança automaticamente quando há falha
    expect(onConcluido).not.toHaveBeenCalled()
    // permite tentar novamente apenas a combinação que falhou
    expect(screen.getByRole('button', { name: /criar 1 variante/i })).toBeInTheDocument()
  })

  it('não tem violações de acessibilidade', async () => {
    const user = userEvent.setup()
    const { container } = render(
      <MatrizVariantesForm produtoId="produto-1" nomeProduto="Legging Fitness" onConcluido={vi.fn()} onPular={vi.fn()} />,
    )
    await gerarMatrizComDuasCores(user)

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
