import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Select } from '@/shared/components/ui/Select'
import { FormField } from '@/shared/components/ui/FormField'
import { AtualizarUsuarioFormSchema, type AtualizarUsuarioFormValues } from '../schemas/usuario.schema'
import { PAPEL_OPCOES } from '../lib/papel-labels'

type Props = {
  defaultValues: AtualizarUsuarioFormValues
  onSubmit: (values: AtualizarUsuarioFormValues) => void
  isSubmitting?: boolean
}

// Edição de nome/papel de um usuário já cadastrado. Não inclui e-mail
// (imutável) nem senha (ver RedefinirSenhaModal, PATCH /usuarios/{id}/senha)
// — mesma separação do contrato de API (docs/openapi.yaml).
export function UsuarioEditForm({ defaultValues, onSubmit, isSubmitting }: Props) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AtualizarUsuarioFormValues>({
    resolver: zodResolver(AtualizarUsuarioFormSchema),
    defaultValues,
  })

  return (
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      <FormField label="Nome completo" htmlFor="nome" required error={errors.nome?.message}>
        <Input
          id="nome"
          autoComplete="name"
          invalid={Boolean(errors.nome)}
          aria-required="true"
          {...register('nome')}
        />
      </FormField>

      <FormField label="Papel" htmlFor="papel" required error={errors.papel?.message}>
        <Select id="papel" invalid={Boolean(errors.papel)} aria-required="true" {...register('papel')}>
          {PAPEL_OPCOES.map((opcao) => (
            <option key={opcao.value} value={opcao.value}>
              {opcao.label}
            </option>
          ))}
        </Select>
      </FormField>

      <Button type="submit" isLoading={isSubmitting} aria-busy={isSubmitting} className="w-full sm:w-auto">
        {isSubmitting ? 'Salvando...' : 'Salvar alterações'}
      </Button>
    </form>
  )
}
