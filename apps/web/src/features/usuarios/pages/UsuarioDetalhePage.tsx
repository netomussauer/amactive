import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Badge } from '@/shared/components/ui/Badge'
import { Button } from '@/shared/components/ui/Button'
import { Spinner } from '@/shared/components/ui/Spinner'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { getErrorMessage } from '@/shared/lib/get-error-message'
import { UsuarioEditForm } from '../components/UsuarioEditForm'
import { RedefinirSenhaModal } from '../components/RedefinirSenhaModal'
import { useUsuario } from '../hooks/useUsuario'
import { useAtualizarUsuario } from '../hooks/useAtualizarUsuario'
import { useInativarUsuario } from '../hooks/useInativarUsuario'
import { useReativarUsuario } from '../hooks/useReativarUsuario'

// Detalhe/edição de um usuário cadastrado (rota restrita a ADMIN, ver
// app/router.tsx RoleGuard). Nome/papel são editados aqui; e-mail é
// imutável (não faz parte de PUT /usuarios/{id}) e senha tem fluxo próprio
// (ver RedefinirSenhaModal).
export function UsuarioDetalhePage() {
  const { usuarioId } = useParams<{ usuarioId: string }>()
  const [isSenhaModalOpen, setIsSenhaModalOpen] = useState(false)

  const { data: usuario, isLoading } = useUsuario(usuarioId)
  const { mutate: atualizar, isPending, error: erroAtualizar } = useAtualizarUsuario(usuarioId ?? '')
  const { mutate: inativar, error: erroInativar } = useInativarUsuario()
  const { mutate: reativar, error: erroReativar } = useReativarUsuario()

  if (isLoading) {
    return (
      <PageWrapper title="Usuário">
        <Spinner label="Carregando usuário..." />
      </PageWrapper>
    )
  }

  if (!usuario) {
    return (
      <PageWrapper title="Usuário">
        <EmptyState
          title="Usuário não encontrado"
          description="Verifique o endereço ou volte para a lista de usuários."
        />
      </PageWrapper>
    )
  }

  // Salvaguarda do backend: não é possível desativar/rebaixar o único ADMIN
  // ativo do sistema (409, ver docs/openapi.yaml info.description). O toast
  // genérico já aparece via shared/lib/query-client.ts; a mensagem inline
  // aqui reforça o motivo exato junto do formulário/ação que falhou.
  const erro = erroAtualizar ?? erroInativar ?? erroReativar

  function handleToggleAtivo() {
    if (!usuario) return
    if (usuario.ativo) {
      if (window.confirm(`Desativar o usuário ${usuario.nome}?`)) inativar(usuario.id)
      return
    }
    reativar({ id: usuario.id, nome: usuario.nome, papel: usuario.papel })
  }

  return (
    <PageWrapper title={usuario.nome} description={usuario.email}>
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Editar dados</CardTitle>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={usuario.ativo ? 'ok' : 'neutral'}>{usuario.ativo ? 'Ativo' : 'Inativo'}</Badge>
            <Button variant="outline" size="sm" onClick={handleToggleAtivo}>
              {usuario.ativo ? 'Desativar' : 'Reativar'}
            </Button>
            <Button variant="outline" size="sm" onClick={() => setIsSenhaModalOpen(true)}>
              Redefinir senha
            </Button>
          </div>
        </CardHeader>

        {erro && (
          <p role="alert" className="mb-4 rounded-md border border-danger bg-bg p-2.5 text-sm text-danger">
            {getErrorMessage(erro)}
          </p>
        )}

        <UsuarioEditForm
          defaultValues={{ nome: usuario.nome, papel: usuario.papel }}
          isSubmitting={isPending}
          onSubmit={(values) => atualizar({ ...values, ativo: usuario.ativo })}
        />
      </Card>

      <RedefinirSenhaModal
        open={isSenhaModalOpen}
        onClose={() => setIsSenhaModalOpen(false)}
        usuarioId={usuario.id}
        usuarioNome={usuario.nome}
      />
    </PageWrapper>
  )
}
