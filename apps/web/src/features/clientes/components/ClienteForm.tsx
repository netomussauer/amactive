import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { CriarClienteSchema, type CriarClienteDTO } from '../schemas/cliente.schema'

type Props = {
  defaultValues?: Partial<CriarClienteDTO>
  onSubmit: (values: CriarClienteDTO) => void
  isSubmitting?: boolean
  submitLabel?: string
}

// Formulário reutilizável de cliente (cadastro e edição).
export function ClienteForm({ defaultValues, onSubmit, isSubmitting, submitLabel = 'Salvar cliente' }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CriarClienteDTO>({
    resolver: zodResolver(CriarClienteSchema),
    defaultValues: {
      nome: '',
      cpf_cnpj: '',
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
      <FormField label="Nome completo" htmlFor="nome" required error={errors.nome?.message}>
        <Input id="nome" autoComplete="name" invalid={Boolean(errors.nome)} aria-required="true" {...register('nome')} />
      </FormField>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <FormField label="CPF/CNPJ" htmlFor="cpf_cnpj" error={errors.cpf_cnpj?.message}>
          <Input id="cpf_cnpj" {...register('cpf_cnpj')} />
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
