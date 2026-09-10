import { useNavigate } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card } from '@/shared/components/ui/Card'
import { routes } from '@/shared/lib/routes'
import { FornecedorForm } from '../components/FornecedorForm'
import { useCriarFornecedor } from '../hooks/useCriarFornecedor'

export function FornecedorNovoPage() {
  const navigate = useNavigate()
  const { mutate, isPending } = useCriarFornecedor()

  return (
    <PageWrapper title="Novo fornecedor" description="Cadastre um novo fornecedor.">
      <Card className="max-w-2xl">
        <FornecedorForm
          isSubmitting={isPending}
          submitLabel="Cadastrar fornecedor"
          onSubmit={(values) =>
            mutate(values, { onSuccess: (fornecedor) => navigate(routes.fornecedorDetalhe(fornecedor.id)) })
          }
        />
      </Card>
    </PageWrapper>
  )
}
