import { useState } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe, toHaveNoViolations } from 'jest-axe'
import { PaletaDeCores } from './PaletaDeCores'

expect.extend(toHaveNoViolations)

// Wrapper controlado — PaletaDeCores é um componente controlado (value/onChange),
// então os testes de interação precisam manter o estado como um consumidor real faria.
function PaletaControlada({
  multiple = true,
  onChangeSpy,
  initialValue = [],
}: {
  multiple?: boolean
  onChangeSpy?: (value: string[]) => void
  initialValue?: string[]
}) {
  const [value, setValue] = useState<string[]>(initialValue)
  return (
    <PaletaDeCores
      idPrefix="teste-cor"
      ariaLabel="Cor"
      multiple={multiple}
      value={value}
      onChange={(next) => {
        setValue(next)
        onChangeSpy?.(next)
      }}
    />
  )
}

describe('PaletaDeCores', () => {
  it('seleciona uma cor da paleta ao clicar (multi-seleção)', async () => {
    const user = userEvent.setup()
    const onChangeSpy = vi.fn()
    render(<PaletaControlada onChangeSpy={onChangeSpy} />)

    await user.click(screen.getByRole('button', { name: 'Coral' }))

    expect(onChangeSpy).toHaveBeenCalledWith(['Coral'])
    expect(screen.getByRole('button', { name: 'Coral' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('permite selecionar mais de uma cor em modo múltiplo', async () => {
    const user = userEvent.setup()
    const onChangeSpy = vi.fn()
    render(<PaletaControlada onChangeSpy={onChangeSpy} />)

    await user.click(screen.getByRole('button', { name: 'Coral' }))
    await user.click(screen.getByRole('button', { name: 'Preto' }))

    expect(onChangeSpy).toHaveBeenLastCalledWith(['Coral', 'Preto'])
  })

  it('desseleciona uma cor já selecionada ao clicar novamente', async () => {
    const user = userEvent.setup()
    const onChangeSpy = vi.fn()
    render(<PaletaControlada onChangeSpy={onChangeSpy} initialValue={['Coral']} />)

    await user.click(screen.getByRole('button', { name: 'Coral' }))

    expect(onChangeSpy).toHaveBeenCalledWith([])
    expect(screen.getByRole('button', { name: 'Coral' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('em modo de seleção única, a nova escolha substitui a anterior', async () => {
    const user = userEvent.setup()
    const onChangeSpy = vi.fn()
    render(<PaletaControlada multiple={false} onChangeSpy={onChangeSpy} />)

    await user.click(screen.getByRole('button', { name: 'Coral' }))
    await user.click(screen.getByRole('button', { name: 'Preto' }))

    expect(onChangeSpy).toHaveBeenLastCalledWith(['Preto'])
    expect(screen.getByRole('button', { name: 'Coral' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: 'Preto' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('permite adicionar uma cor personalizada fora da paleta pré-definida', async () => {
    const user = userEvent.setup()
    const onChangeSpy = vi.fn()
    render(<PaletaControlada onChangeSpy={onChangeSpy} />)

    await user.click(screen.getByRole('button', { name: 'Personalizada' }))
    await user.type(screen.getByLabelText(/nome da cor personalizada/i), 'Terracota')
    await user.keyboard('{Enter}')

    expect(onChangeSpy).toHaveBeenCalledWith(['Terracota'])
    // A cor personalizada passa a aparecer como um swatch selecionado e removível.
    expect(screen.getByRole('button', { name: /terracota/i })).toHaveAttribute('aria-pressed', 'true')
  })

  it('remove uma cor personalizada ao clicar novamente em seu swatch', async () => {
    const user = userEvent.setup()
    const onChangeSpy = vi.fn()
    render(<PaletaControlada onChangeSpy={onChangeSpy} initialValue={['Terracota']} />)

    await user.click(screen.getByRole('button', { name: /terracota/i }))

    expect(onChangeSpy).toHaveBeenCalledWith([])
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(<PaletaControlada initialValue={['Coral']} />)
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('não tem violações de acessibilidade com o campo de cor personalizada aberto', async () => {
    const user = userEvent.setup()
    const { container } = render(<PaletaControlada />)
    await user.click(screen.getByRole('button', { name: 'Personalizada' }))

    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })
})
