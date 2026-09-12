import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { axe, toHaveNoViolations } from 'jest-axe'
import { ImagemGaleriaCor } from './ImagemGaleriaCor'
import type { Imagem } from '../types/imagem.types'

expect.extend(toHaveNoViolations)

const uploadMock = vi.fn()
const definirPrincipalMock = vi.fn()
const atualizarOrdemMock = vi.fn()
const removerMock = vi.fn()

vi.mock('../hooks/useUploadImagem', () => ({
  useUploadImagem: () => ({ mutate: uploadMock, isPending: false, error: null }),
}))
vi.mock('../hooks/useDefinirImagemPrincipal', () => ({
  useDefinirImagemPrincipal: () => ({ mutate: definirPrincipalMock }),
}))
vi.mock('../hooks/useAtualizarOrdemImagem', () => ({
  useAtualizarOrdemImagem: () => ({ mutate: atualizarOrdemMock }),
}))
vi.mock('../hooks/useRemoverImagem', () => ({
  useRemoverImagem: () => ({ mutate: removerMock }),
}))

function makeImagem(overrides: Partial<Imagem> = {}): Imagem {
  return {
    id: 'imagem-1',
    produto_id: 'produto-1',
    cor: 'Coral',
    url: '/media/produtos/produto-1/foto.jpg',
    ordem: 0,
    principal: false,
    criado_em: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

function makeFile({ type = 'image/jpeg', size = 1024, name = 'foto.jpg' } = {}): File {
  const blob = new Blob([new Uint8Array(size)], { type })
  return new File([blob], name, { type })
}

describe('ImagemGaleriaCor', () => {
  beforeEach(() => {
    uploadMock.mockClear()
    definirPrincipalMock.mockClear()
    atualizarOrdemMock.mockClear()
    removerMock.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('exibe estado vazio quando a cor ainda não tem imagens', () => {
    render(<ImagemGaleriaCor produtoId="produto-1" cor="Coral" imagens={[]} podeEditar />)
    expect(screen.getByText(/nenhuma imagem cadastrada para esta cor/i)).toBeInTheDocument()
  })

  it('indica visualmente qual imagem é a principal', () => {
    render(
      <ImagemGaleriaCor
        produtoId="produto-1"
        cor="Coral"
        imagens={[makeImagem({ id: 'a', principal: true }), makeImagem({ id: 'b', ordem: 1 })]}
        podeEditar
      />,
    )
    expect(screen.getByLabelText(/imagem principal desta cor/i)).toBeInTheDocument()
    // só a imagem 2 (não principal) oferece a ação de definir como principal
    expect(screen.getAllByRole('button', { name: /definir imagem .* como principal/i })).toHaveLength(1)
  })

  it('envia um arquivo válido para upload com a cor correta', async () => {
    const user = userEvent.setup()
    render(<ImagemGaleriaCor produtoId="produto-1" cor="Coral" imagens={[]} podeEditar />)

    const input = screen.getByLabelText(/enviar imagem para a cor coral/i, { selector: 'input' })
    await user.upload(input, makeFile())

    expect(uploadMock).toHaveBeenCalledWith({ cor: 'Coral', arquivo: expect.any(File) })
  })

  it('bloqueia upload de arquivo inválido e mostra a mensagem de erro sem chamar a API', () => {
    render(<ImagemGaleriaCor produtoId="produto-1" cor="Coral" imagens={[]} podeEditar />)

    // fireEvent (em vez de userEvent.upload) simula um arquivo que não bate
    // com o `accept` do input — cenário real via drag-and-drop ou seletor
    // "todos os arquivos" do SO, que ainda precisa da validação client-side.
    const input = screen.getByLabelText(/enviar imagem para a cor coral/i, { selector: 'input' })
    fireEvent.change(input, { target: { files: [makeFile({ type: 'application/pdf' })] } })

    expect(screen.getByText(/formato inválido/i)).toBeInTheDocument()
    expect(uploadMock).not.toHaveBeenCalled()
  })

  it('define uma imagem como principal ao clicar na ação', async () => {
    const user = userEvent.setup()
    render(<ImagemGaleriaCor produtoId="produto-1" cor="Coral" imagens={[makeImagem({ id: 'imagem-9' })]} podeEditar />)

    await user.click(screen.getByRole('button', { name: /definir imagem 1 da cor coral como principal/i }))

    expect(definirPrincipalMock).toHaveBeenCalledWith('imagem-9')
  })

  it('remove a imagem somente após confirmação', async () => {
    const user = userEvent.setup()
    vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)

    render(<ImagemGaleriaCor produtoId="produto-1" cor="Coral" imagens={[makeImagem({ id: 'imagem-9' })]} podeEditar />)

    const botaoRemover = screen.getByRole('button', { name: /remover imagem 1 da cor coral/i })
    await user.click(botaoRemover)
    expect(removerMock).not.toHaveBeenCalled()

    await user.click(botaoRemover)
    expect(removerMock).toHaveBeenCalledWith('imagem-9')
  })

  it('não tem violações de acessibilidade', async () => {
    const { container } = render(
      <ImagemGaleriaCor
        produtoId="produto-1"
        cor="Coral"
        imagens={[makeImagem({ id: 'a', principal: true }), makeImagem({ id: 'b', ordem: 1 })]}
        podeEditar
      />,
    )
    const results = await axe(container)
    expect(results).toHaveNoViolations()
  })

  it('oculta upload e ações de escrita (reordenar/definir principal/remover) quando podeEditar é false', () => {
    render(
      <ImagemGaleriaCor
        produtoId="produto-1"
        cor="Coral"
        imagens={[makeImagem({ id: 'a', principal: true }), makeImagem({ id: 'b', ordem: 1 })]}
        podeEditar={false}
      />,
    )

    expect(screen.queryByLabelText(/enviar imagem para a cor coral/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /mover imagem/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /definir imagem .* como principal/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /remover imagem/i })).not.toBeInTheDocument()
    // a imagem principal continua visível — é leitura, não escrita
    expect(screen.getByLabelText(/imagem principal desta cor/i)).toBeInTheDocument()
  })
})
