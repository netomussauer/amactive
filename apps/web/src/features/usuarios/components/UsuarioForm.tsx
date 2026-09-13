import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Select } from '@/shared/components/ui/Select'
import { FormField } from '@/shared/components/ui/FormField'
import { ApiError } from '@/shared/lib/api-client'
import { PapelUsuario } from '@/shared/types/api.types'
import { useCriarUsuario } from '../hooks/useCriarUsuario'
import { CriarUsuarioSchema, type CriarUsuarioDTO } from '../schemas/usuario.schema'
import { PAPEL_OPCOES } from '../lib/papel-labels'
import type { UsuarioDetalhe } from '../types/usuario.types'

type Props = {
  onSuccess: (usuario: UsuarioDetalhe) => void
}

// Formulário de cadastro de usuário (nome, e-mail, senha inicial, papel).
// A edição (nome + papel, sem e-mail/senha) usa UsuarioEditForm — a API não
// aceita e-mail nem senha em PUT /usuarios/{id} (ver docs/openapi.yaml).
export function UsuarioForm({ onSuccess }: Props) {
  const { mutate, isPending } = useCriarUsuario()

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<CriarUsuarioDTO>({
    resolver: zodResolver(CriarUsuarioSchema),
    defaultValues: { nome: '', email: '', senha: '', papel: PapelUsuario.VENDEDOR },
  })

  function handleFormSubmit(values: CriarUsuarioDTO) {
    mutate(values, {
      onSuccess,
      onError: (error) => {
        // 409 = e-mail já cadastrado para outro usuário (ver docs/openapi.yaml
        // POST /usuarios). O toast de erro genérico já aparece via
        // shared/lib/query-client.ts; aqui marcamos o campo específico para
        // o usuário corrigir sem precisar adivinhar qual campo errou.
        const detail = error instanceof ApiError ? error.detail : undefined
        setError('email', { message: detail ?? 'Não foi possível cadastrar. Verifique o e-mail informado.' })
      },
    })
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit(handleFormSubmit)} noValidate>
      <FormField label="Nome completo" htmlFor="nome" required error={errors.nome?.message}>
        <Input
          id="nome"
          autoComplete="name"
          invalid={Boolean(errors.nome)}
          aria-required="true"
          {...register('nome')}
        />
      </FormField>

      <FormField label="E-mail" htmlFor="email" required error={errors.email?.message}>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          invalid={Boolean(errors.email)}
          aria-required="true"
          {...register('email')}
        />
      </FormField>

      <FormField
        label="Senha inicial"
        htmlFor="senha"
        required
        error={errors.senha?.message}
        hint="Mínimo de 8 caracteres. O usuário pode alterá-la depois de entrar."
      >
        <Input
          id="senha"
          type="password"
          autoComplete="new-password"
          invalid={Boolean(errors.senha)}
          aria-required="true"
          {...register('senha')}
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

      <Button type="submit" isLoading={isPending} aria-busy={isPending} className="w-full sm:w-auto">
        {isPending ? 'Cadastrando...' : 'Cadastrar usuário'}
      </Button>
    </form>
  )
}
