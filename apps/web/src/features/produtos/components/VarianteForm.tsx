import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { CriarVarianteSchema, type CriarVarianteDTO } from '../schemas/produto.schema'
import { TAMANHOS_SUGERIDOS } from '../lib/matriz-variantes'

type Props = {
  onSubmit: (values: CriarVarianteDTO) => void
  isSubmitting?: boolean
}

export function VarianteForm({ onSubmit, isSubmitting }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CriarVarianteDTO>({
    resolver: zodResolver(CriarVarianteSchema),
    defaultValues: {
      sku: '',
      tamanho: 'M',
      cor: '',
      preco_venda: '',
      preco_custo: '',
      estoque_inicial: 0,
    },
  })

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      <div className="grid grid-cols-2 gap-4">
        <FormField
          label="Tamanho"
          htmlFor="tamanho"
          required
          error={errors.tamanho?.message}
          hint={`Sugestões: ${TAMANHOS_SUGERIDOS.join(', ')}`}
        >
          <Input id="tamanho" list="tamanhos-sugeridos" invalid={Boolean(errors.tamanho)} {...register('tamanho')} />
          <datalist id="tamanhos-sugeridos">
            {TAMANHOS_SUGERIDOS.map((tamanho) => (
              <option key={tamanho} value={tamanho} />
            ))}
          </datalist>
        </FormField>

        <FormField label="Cor" htmlFor="cor" required error={errors.cor?.message}>
          <Input id="cor" placeholder="Coral" invalid={Boolean(errors.cor)} {...register('cor')} />
        </FormField>
      </div>

      <FormField label="SKU" htmlFor="sku" hint="Deixe em branco para gerar automaticamente" error={errors.sku?.message}>
        <Input id="sku" placeholder="LEG-CORAL-M" {...register('sku')} />
      </FormField>

      <div className="grid grid-cols-2 gap-4">
        <FormField label="Preço de venda" htmlFor="preco_venda" required error={errors.preco_venda?.message}>
          <Input
            id="preco_venda"
            placeholder="129.90"
            invalid={Boolean(errors.preco_venda)}
            aria-required="true"
            {...register('preco_venda')}
          />
        </FormField>

        <FormField label="Preço de custo" htmlFor="preco_custo" error={errors.preco_custo?.message}>
          <Input id="preco_custo" placeholder="60.00" {...register('preco_custo')} />
        </FormField>
      </div>

      <FormField
        label="Estoque inicial"
        htmlFor="estoque_inicial"
        hint="Gera uma movimentação de entrada automática"
        error={errors.estoque_inicial?.message}
      >
        <Input
          id="estoque_inicial"
          type="number"
          min={0}
          {...register('estoque_inicial', { valueAsNumber: true })}
        />
      </FormField>

      <Button type="submit" isLoading={isSubmitting} aria-busy={isSubmitting} className="w-full">
        {isSubmitting ? 'Salvando...' : 'Cadastrar variante'}
      </Button>
    </form>
  )
}
