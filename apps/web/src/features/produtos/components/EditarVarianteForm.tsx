import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { TAMANHOS_SUGERIDOS } from '../lib/matriz-variantes'
import type { AtualizarVarianteDTO } from '../schemas/produto.schema'

// Edição de uma variante já cadastrada. O ESTOQUE NÃO ENTRA AQUI: reposição é
// uma movimentação de entrada (Estoque > Movimentações), para manter o histórico.
const FormSchema = z.object({
  sku: z.string().trim().min(1, 'Informe o SKU').max(50, 'Use no máximo 50 caracteres'),
  tamanho: z.string().trim().min(1, 'Informe o tamanho').max(10, 'Use no máximo 10 caracteres'),
  cor: z.string().trim().min(1, 'Informe a cor').max(50, 'Use no máximo 50 caracteres'),
  preco_venda: z.string().regex(/^\d+\.\d{2}$/, 'Use o formato 0.00'),
  preco_custo: z.string().regex(/^(\d+\.\d{2})?$/, 'Use o formato 0.00').optional(),
})
type FormValues = z.infer<typeof FormSchema>

export type VarianteEditavel = {
  sku: string
  tamanho: string
  cor: string
  preco_venda: string
  preco_custo?: string | null
}

type Props = {
  variante: VarianteEditavel
  isSubmitting?: boolean
  onSubmit: (payload: AtualizarVarianteDTO) => void
  onCancel: () => void
}

export function EditarVarianteForm({ variante, isSubmitting, onSubmit, onCancel }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(FormSchema),
    defaultValues: {
      sku: variante.sku,
      tamanho: variante.tamanho,
      cor: variante.cor,
      preco_venda: variante.preco_venda,
      preco_custo: variante.preco_custo ?? '',
    },
  })

  function enviar(valores: FormValues) {
    onSubmit({
      sku: valores.sku,
      tamanho: valores.tamanho,
      cor: valores.cor,
      preco_venda: valores.preco_venda,
      // Campo vazio remove o custo cadastrado; o backend aceita null.
      preco_custo: valores.preco_custo ? valores.preco_custo : null,
    })
  }

  return (
    <form className="flex flex-col gap-4" onSubmit={handleSubmit(enviar)} noValidate>
      <FormField label="SKU" htmlFor="editar-sku" required error={errors.sku?.message}>
        <Input id="editar-sku" invalid={Boolean(errors.sku)} {...register('sku')} />
      </FormField>
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Tamanho" htmlFor="editar-tamanho" required error={errors.tamanho?.message}>
          <Input id="editar-tamanho" list="editar-tamanhos-sugeridos" invalid={Boolean(errors.tamanho)} {...register('tamanho')} />
          <datalist id="editar-tamanhos-sugeridos">
            {TAMANHOS_SUGERIDOS.map((tamanho) => (
              <option key={tamanho} value={tamanho} />
            ))}
          </datalist>
        </FormField>
        <FormField label="Cor" htmlFor="editar-cor" required error={errors.cor?.message}>
          <Input id="editar-cor" invalid={Boolean(errors.cor)} {...register('cor')} />
        </FormField>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <FormField label="Preço de venda" htmlFor="editar-preco-venda" required error={errors.preco_venda?.message}>
          <Input id="editar-preco-venda" placeholder="99.90" invalid={Boolean(errors.preco_venda)} {...register('preco_venda')} />
        </FormField>
        <FormField label="Preço de custo" htmlFor="editar-preco-custo" error={errors.preco_custo?.message}>
          <Input id="editar-preco-custo" placeholder="60.00" invalid={Boolean(errors.preco_custo)} {...register('preco_custo')} />
        </FormField>
      </div>
      <p className="rounded-md border border-border bg-bg-subtle p-3 text-xs text-text-muted">
        O estoque não muda por aqui. Para repor peças, registre uma entrada em Estoque › Movimentações.
      </p>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
        <Button type="submit" isLoading={isSubmitting}>
          Salvar alterações
        </Button>
      </div>
    </form>
  )
}
