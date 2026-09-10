import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Select } from '@/shared/components/ui/Select'
import { Textarea } from '@/shared/components/ui/Textarea'
import { FormField } from '@/shared/components/ui/FormField'
import { useCategorias } from '../hooks/useCategorias'
import { CriarProdutoSchema, type CriarProdutoDTO } from '../schemas/produto.schema'

type Props = {
  defaultValues?: Partial<CriarProdutoDTO>
  onSubmit: (values: CriarProdutoDTO) => void
  isSubmitting?: boolean
  submitLabel?: string
}

export function ProdutoForm({ defaultValues, onSubmit, isSubmitting, submitLabel = 'Salvar produto' }: Props) {
  const { data: categorias } = useCategorias()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CriarProdutoDTO>({
    resolver: zodResolver(CriarProdutoSchema),
    defaultValues: {
      nome: '',
      descricao: '',
      categoria_id: null,
      marca: 'AMACTIVE',
      ...defaultValues,
    },
  })

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      <FormField label="Nome do produto" htmlFor="nome" required error={errors.nome?.message}>
        <Input
          id="nome"
          placeholder="Legging Fitness Alta Compressão"
          invalid={Boolean(errors.nome)}
          aria-required="true"
          {...register('nome')}
        />
      </FormField>

      <FormField label="Descrição" htmlFor="descricao" error={errors.descricao?.message}>
        <Textarea id="descricao" placeholder="Detalhes do produto" {...register('descricao')} />
      </FormField>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField label="Marca" htmlFor="marca" error={errors.marca?.message}>
          <Input id="marca" {...register('marca')} />
        </FormField>

        <FormField label="Categoria" htmlFor="categoria_id" error={errors.categoria_id?.message}>
          <Select
            id="categoria_id"
            defaultValue={defaultValues?.categoria_id ?? ''}
            {...register('categoria_id', { setValueAs: (value: string) => (value === '' ? null : value) })}
          >
            <option value="">Sem categoria</option>
            {categorias?.data.map((categoria) => (
              <option key={categoria.id} value={categoria.id}>
                {categoria.nome}
              </option>
            ))}
          </Select>
        </FormField>
      </div>

      <Button type="submit" isLoading={isSubmitting} aria-busy={isSubmitting} className="w-full sm:w-auto">
        {isSubmitting ? 'Salvando...' : submitLabel}
      </Button>
    </form>
  )
}
