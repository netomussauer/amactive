import { useParams } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Badge } from '@/shared/components/ui/Badge'
import { Button } from '@/shared/components/ui/Button'
import { Spinner } from '@/shared/components/ui/Spinner'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { ClienteForm } from '../components/ClienteForm'
import { useCliente } from '../hooks/useCliente'
import { useAtualizarCliente } from '../hooks/useAtualizarCliente'
import { useInativarCliente } from '../hooks/useInativarCliente'

// Detalhe/edição de um cliente cadastrado.
export function ClienteDetalhePage() {
  const { clienteId } = useParams<{ clienteId: string }>()
  const { data: cliente, isLoading } = useCliente(clienteId)
  const { mutate: atualizar, isPending } = useAtualizarCliente(clienteId ?? '')
  const { mutate: inativar } = useInativarCliente()

  if (isLoading) {
    return (
      <PageWrapper title="Cliente">
        <Spinner label="Carregando cliente..." />
      </PageWrapper>
    )
  }

  if (!cliente) {
    return (
      <PageWrapper title="Cliente">
        <EmptyState title="Cliente não encontrado" description="Verifique o endereço ou volte para a lista de clientes." />
      </PageWrapper>
    )
  }

  return (
    <PageWrapper title={cliente.nome} description="Dados cadastrais do cliente.">
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Editar dados</CardTitle>
          <div className="flex items-center gap-2">
            <Badge tone={cliente.ativo ? 'ok' : 'neutral'}>{cliente.ativo ? 'Ativo' : 'Inativo'}</Badge>
            {cliente.ativo && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (window.confirm(`Inativar o cliente ${cliente.nome}?`)) inativar(cliente.id)
                }}
              >
                Inativar
              </Button>
            )}
          </div>
        </CardHeader>
        <ClienteForm
          defaultValues={cliente}
          isSubmitting={isPending}
          submitLabel="Salvar alterações"
          onSubmit={(values) => atualizar(values)}
        />
      </Card>
    </PageWrapper>
  )
}
