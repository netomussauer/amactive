import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { axe, toHaveNoViolations } from 'jest-axe'
import { Stepper, type StepperStep } from './Stepper'

expect.extend(toHaveNoViolations)

const STEPS: StepperStep[] = [
  { id: 'dados', label: 'Dados do produto' },
  { id: 'variantes', label: 'Variantes (cor × tamanho)' },
  { id: 'imagens', label: 'Imagens' },
]

describe('Stepper', () => {
  it('marca a etapa atual com aria-current="step"', () => {
    render(<Stepper steps={STEPS} currentStepId="variantes" />)

    const itemAtual = screen.getByText('Variantes (cor × tamanho)').closest('li')
    expect(itemAtual).toHaveAttribute('aria-current', 'step')
  })

  it('indica etapas anteriores como concluídas e as seguintes como pendentes', () => {
    render(<Stepper steps={STEPS} currentStepId="variantes" />)

    const itemDados = screen.getByText('Dados do produto').closest('li')
    const itemImagens = screen.getByText('Imagens').closest('li')

    expect(itemDados).not.toHaveAttribute('aria-current')
    expect(itemImagens).not.toHaveAttribute('aria-current')
    // Estado é comunicado por texto (sr-only), não apenas por cor.
    expect(screen.getByText('(Concluído)', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('(Pendente)', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('(Etapa atual)', { exact: false })).toBeInTheDocument()
  })

  it('marca a primeira etapa como atual quando currentStepId é o primeiro passo', () => {
    render(<Stepper steps={STEPS} currentStepId="dados" />)

    expect(screen.getByText('Dados do produto').closest('li')).toHaveAttribute('aria-current', 'step')
    expect(screen.queryByText('(Concluído)', { exact: false })).not.toBeInTheDocument()
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(<Stepper steps={STEPS} currentStepId="variantes" />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
