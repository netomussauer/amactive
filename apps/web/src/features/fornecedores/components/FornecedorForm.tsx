import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { CriarFornecedorSchema, type CriarFornecedorDTO } from '../schemas/fornecedor.schema'

type Props = {
  defaultValues?: Partial<CriarFornecedorDTO>
  onSubmit: (values: CriarFornecedorDTO) => void
  isSubmitting?: boolean
  submitLabel?: string
}

export function FornecedorForm({ defaultValues, onSubmit, isSubmitting, submitLabel = 'Salvar fornecedor' }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CriarFornecedorDTO>({
    resolver: zodResolver(CriarFornecedorSchema),
    defaultValues: {
      razao_social: '',
      nome_fantasia: '',
      cnpj: '',
      email: '',
      telefone: '',
      endereco_logradouro: '',
      endereco_cidade: '',
      endereco_uf: '',
      endereco_cep: '',
      ...defaultValues,
    },
  })

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      <FormField label="Razão social" htmlFor="razao_social" required error={errors.razao_social?.message}>
        <Input id="razao_social" invalid={Boolean(errors.razao_social)} aria-required="true" {...register('razao_social')} />
      </FormField>

      <FormField label="Nome fantasia" htmlFor="nome_fantasia" error={errors.nome_fantasia?.message}>
        <Input id="nome_fantasia" {...register('nome_fantasia')} />
      </FormField>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField label="CNPJ" htmlFor="cnpj" error={errors.cnpj?.message}>
          <Input id="cnpj" {...register('cnpj')} />
        </FormField>
        <FormField label="Telefone" htmlFor="telefone" error={errors.telefone?.message}>
          <Input id="telefone" autoComplete="tel" {...register('telefone')} />
        </FormField>
      </div>

      <FormField label="E-mail" htmlFor="email" error={errors.email?.message}>
        <Input id="email" type="email" autoComplete="email" invalid={Boolean(errors.email)} {...register('email')} />
      </FormField>

      <FormField label="Endereço" htmlFor="endereco_logradouro" error={errors.endereco_logradouro?.message}>
        <Input id="endereco_logradouro" {...register('endereco_logradouro')} />
      </FormField>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <FormField label="Cidade" htmlFor="endereco_cidade" error={errors.endereco_cidade?.message}>
          <Input id="endereco_cidade" {...register('endereco_cidade')} />
        </FormField>
        <FormField label="UF" htmlFor="endereco_uf" error={errors.endereco_uf?.message}>
          <Input id="endereco_uf" maxLength={2} className="uppercase" {...register('endereco_uf')} />
        </FormField>
        <FormField label="CEP" htmlFor="endereco_cep" error={errors.endereco_cep?.message}>
          <Input id="endereco_cep" {...register('endereco_cep')} />
        </FormField>
      </div>

      <Button type="submit" isLoading={isSubmitting} aria-busy={isSubmitting} className="w-full sm:w-auto">
        {isSubmitting ? 'Salvando...' : submitLabel}
      </Button>
    </form>
  )
}
