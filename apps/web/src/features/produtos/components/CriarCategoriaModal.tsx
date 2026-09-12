import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Modal } from '@/shared/components/ui/Modal'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { ApiError } from '@/shared/lib/api-client'
import { useCriarCategoria } from '../hooks/useCriarCategoria'
import { CriarCategoriaSchema, type CriarCategoriaDTO, type Categoria } from '../schemas/produto.schema'

type Props = {
  open: boolean
  onClose: () => void
  categoriasExistentes: Categoria[]
  onCriada: (categoria: Categoria) => void
}

// Modal de criação rápida de categoria, aberto a partir do ProdutoForm — evita
// que o usuário precise chamar POST /categorias na mão para cadastrar uma
// categoria nova antes de conseguir vinculá-la a um produto.
export function CriarCategoriaModal({ open, onClose, categoriasExistentes, onCriada }: Props) {
  const { mutate, isPending } = useCriarCategoria()

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<CriarCategoriaDTO>({
    resolver: zodResolver(CriarCategoriaSchema),
    defaultValues: { nome: '' },
  })

  function handleClose() {
    reset()
    onClose()
  }

  function handleFormSubmit(values: CriarCategoriaDTO) {
    const nomeNormalizado = values.nome.trim().toLowerCase()
    const jaExiste = categoriasExistentes.some(
      (categoria) => categoria.nome.trim().toLowerCase() === nomeNormalizado,
    )
    // Checagem client-side com a lista já carregada — evita um round-trip
    // desnecessário para o caso comum. O nome/slug também são UNIQUE no
    // banco, então o erro do backend (abaixo) cobre o caso de corrida entre
    // dois usuários cadastrando a mesma categoria ao mesmo tempo.
    if (jaExiste) {
      setError('nome', { message: 'Já existe uma categoria com esse nome' })
      return
    }

    mutate(values, {
      onSuccess: (categoria) => {
        reset()
        onCriada(categoria)
        onClose()
      },
      onError: (error) => {
        const detail = error instanceof ApiError ? error.detail : undefined
        setError('nome', {
          message: detail ?? 'Não foi possível criar a categoria. Verifique se o nome já não está em uso.',
        })
      },
    })
  }

  return (
    <Modal open={open} onClose={handleClose} title="Nova categoria">
      <form className="space-y-4" onSubmit={handleSubmit(handleFormSubmit)} noValidate>
        <FormField label="Nome da categoria" htmlFor="categoria-nome" required error={errors.nome?.message}>
          <Input
            id="categoria-nome"
            placeholder="Leggings"
            invalid={Boolean(errors.nome)}
            aria-required="true"
            autoFocus
            {...register('nome')}
          />
        </FormField>

        <Button type="submit" isLoading={isPending} aria-busy={isPending} className="w-full">
          {isPending ? 'Criando...' : 'Criar categoria'}
        </Button>
      </form>
    </Modal>
  )
}
