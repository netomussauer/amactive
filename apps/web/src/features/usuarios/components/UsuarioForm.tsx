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
        // Só um 409 (e-mail já cadastrado, ver docs/openapi.yaml POST
        // /usuarios) é, de fato, um problema NO CAMPO de e-mail — aí faz
        // sentido marcar o campo para o usuário corrigir. Qualquer outro
        // erro (rede, 5xx, etc.) NÃO pode ser atribuído ao e-mail: nada
        // garante que o cadastro falhou de verdade (ex.: "Failed to fetch"
        // pode significar que a resposta se perdeu DEPOIS de a API já ter
        // criado o usuário — o card mentiria dizendo "verifique o e-mail"
        // sobre um cadastro que já existe). Nesses casos, o toast genérico
        // de shared/lib/query-client.ts (via getErrorMessage) já mostra a
        // mensagem real — não duplicar nem inventar uma causa aqui.
        if (error instanceof ApiError && error.status === 409) {
          setError('email', { message: error.detail ?? 'Este e-mail já está em uso por outro usuário.' })
        }
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
