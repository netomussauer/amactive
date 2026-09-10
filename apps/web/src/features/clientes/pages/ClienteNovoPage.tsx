import { useNavigate } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card } from '@/shared/components/ui/Card'
import { routes } from '@/shared/lib/routes'
import { ClienteForm } from '../components/ClienteForm'
import { useCriarCliente } from '../hooks/useCriarCliente'

export function ClienteNovoPage() {
  const navigate = useNavigate()
  const { mutate, isPending } = useCriarCliente()

  return (
    <PageWrapper title="Novo cliente" description="Cadastre um novo cliente.">
      <Card className="max-w-2xl">
        <ClienteForm
          isSubmitting={isPending}
          submitLabel="Cadastrar cliente"
          onSubmit={(values) => mutate(values, { onSuccess: (cliente) => navigate(routes.clienteDetalhe(cliente.id)) })}
        />
      </Card>
    </PageWrapper>
  )
}
