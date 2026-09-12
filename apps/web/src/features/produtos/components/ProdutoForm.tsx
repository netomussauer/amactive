import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Plus } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Select } from '@/shared/components/ui/Select'
import { Textarea } from '@/shared/components/ui/Textarea'
import { FormField } from '@/shared/components/ui/FormField'
import { useCategorias } from '../hooks/useCategorias'
import { CriarProdutoSchema, type CriarProdutoDTO, type Categoria } from '../schemas/produto.schema'
import { CriarCategoriaModal } from './CriarCategoriaModal'

type Props = {
  defaultValues?: Partial<CriarProdutoDTO>
  onSubmit: (values: CriarProdutoDTO) => void
  isSubmitting?: boolean
  submitLabel?: string
}

export function ProdutoForm({ defaultValues, onSubmit, isSubmitting, submitLabel = 'Salvar produto' }: Props) {
  const { data: categorias } = useCategorias()
  const [isCategoriaModalOpen, setIsCategoriaModalOpen] = useState(false)
  // Categoria recém-criada pelo modal — mesclada na lista de opções para
  // aparecer selecionável de imediato, sem esperar o refetch de ['categorias'].
  const [categoriaRecemCriada, setCategoriaRecemCriada] = useState<Categoria | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<CriarProdutoDTO>({
    resolver: zodResolver(CriarProdutoSchema),
    defaultValues: {
      nome: '',
      descricao: '',
      categoria_id: null,
      marca: 'AMACTIVE',
      desconto_percentual: null,
      ...defaultValues,
    },
  })

  const listaCategorias = categorias?.data
  const opcoesCategorias = useMemo(() => {
    const lista = listaCategorias ?? []
    if (categoriaRecemCriada && !lista.some((categoria) => categoria.id === categoriaRecemCriada.id)) {
      return [...lista, categoriaRecemCriada]
    }
    return lista
    // Depende de `listaCategorias` (o array retornado pelo TanStack Query,
    // estável via structural sharing quando o conteúdo não muda) em vez do
    // objeto de resultado inteiro do useQuery — evitar isso recalcula (e
    // recria a array) a cada render e realimenta o useEffect abaixo em loop.
  }, [listaCategorias, categoriaRecemCriada])

  // O <select> de categoria é não-controlado (register), então selecionar a
  // categoria recém-criada precisa esperar o <option> correspondente existir
  // no DOM (commit de opcoesCategorias) antes de mexer no valor via setValue
  // — mesmo padrão usado em MovimentacaoModal para popular variante_id.
  useEffect(() => {
    if (!categoriaRecemCriada) return
    if (opcoesCategorias.some((categoria) => categoria.id === categoriaRecemCriada.id)) {
      setValue('categoria_id', categoriaRecemCriada.id, { shouldValidate: true })
    }
  }, [categoriaRecemCriada, opcoesCategorias, setValue])

  function handleCategoriaCriada(categoria: Categoria) {
    setCategoriaRecemCriada(categoria)
    setIsCategoriaModalOpen(false)
  }

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
          <div className="flex items-start gap-2">
            <Select
              id="categoria_id"
              defaultValue={defaultValues?.categoria_id ?? ''}
              className="flex-1"
              {...register('categoria_id', { setValueAs: (value: string) => (value === '' ? null : value) })}
            >
              <option value="">Sem categoria</option>
              {opcoesCategorias.map((categoria) => (
                <option key={categoria.id} value={categoria.id}>
                  {categoria.nome}
                </option>
              ))}
            </Select>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-10 shrink-0"
              onClick={() => setIsCategoriaModalOpen(true)}
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Nova categoria
            </Button>
          </div>
        </FormField>
      </div>

      <CriarCategoriaModal
        open={isCategoriaModalOpen}
        onClose={() => setIsCategoriaModalOpen(false)}
        categoriasExistentes={categorias?.data ?? []}
        onCriada={handleCategoriaCriada}
      />

      <FormField
        label="Desconto promocional (%)"
        htmlFor="desconto_percentual"
        hint="Opcional — deixe em branco para não aplicar promoção"
        error={errors.desconto_percentual?.message}
      >
        <Input
          id="desconto_percentual"
          type="number"
          min={0.01}
          max={100}
          step="0.01"
          placeholder="Ex: 15"
          invalid={Boolean(errors.desconto_percentual)}
          {...register('desconto_percentual', {
            setValueAs: (value: string) => (value === '' ? null : Number(value)),
          })}
        />
      </FormField>

      <Button type="submit" isLoading={isSubmitting} aria-busy={isSubmitting} className="w-full sm:w-auto">
        {isSubmitting ? 'Salvando...' : submitLabel}
      </Button>
    </form>
  )
}
