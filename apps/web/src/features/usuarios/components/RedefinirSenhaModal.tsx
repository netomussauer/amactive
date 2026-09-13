import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Modal } from '@/shared/components/ui/Modal'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { useRedefinirSenhaUsuario } from '../hooks/useRedefinirSenhaUsuario'
import { RedefinirSenhaSchema, type RedefinirSenhaDTO } from '../schemas/usuario.schema'

type Props = {
  open: boolean
  onClose: () => void
  usuarioId: string
  usuarioNome: string
}

// Reset administrativo DIRETO de senha (PATCH /usuarios/{id}/senha) — o
// ADMIN define uma senha nova para o usuário sem precisar da senha antiga.
// Importante: não é o fluxo de "esqueci minha senha" — não envia e-mail, e a
// senha nova já vale imediatamente após o submit.
export function RedefinirSenhaModal({ open, onClose, usuarioId, usuarioNome }: Props) {
  const { mutate, isPending } = useRedefinirSenhaUsuario(usuarioId)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<RedefinirSenhaDTO>({
    resolver: zodResolver(RedefinirSenhaSchema),
    defaultValues: { senha: '' },
  })

  function handleClose() {
    reset()
    onClose()
  }

  function handleFormSubmit(values: RedefinirSenhaDTO) {
    mutate(values, {
      onSuccess: () => {
        reset()
        onClose()
      },
    })
  }

  return (
    <Modal open={open} onClose={handleClose} title={`Redefinir senha de ${usuarioNome}`}>
      <p className="mb-4 text-sm text-text-muted">
        Reset administrativo imediato: a nova senha passa a valer na hora, sem exigir a senha atual e sem
        enviar nenhum e-mail de recuperação para {usuarioNome}. Isto não é o fluxo de "esqueci minha senha".
      </p>
      <form className="space-y-4" onSubmit={handleSubmit(handleFormSubmit)} noValidate>
        <FormField
          label="Nova senha"
          htmlFor="senha"
          required
          error={errors.senha?.message}
          hint="Mínimo de 8 caracteres."
        >
          <Input
            id="senha"
            type="password"
            autoComplete="new-password"
            invalid={Boolean(errors.senha)}
            aria-required="true"
            autoFocus
            {...register('senha')}
          />
        </FormField>

        <Button type="submit" isLoading={isPending} aria-busy={isPending} className="w-full">
          {isPending ? 'Redefinindo...' : 'Redefinir senha'}
        </Button>
      </form>
    </Modal>
  )
}
