import { useParams } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Badge } from '@/shared/components/ui/Badge'
import { Button } from '@/shared/components/ui/Button'
import { Spinner } from '@/shared/components/ui/Spinner'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { FornecedorForm } from '../components/FornecedorForm'
import { useFornecedor } from '../hooks/useFornecedor'
import { useAtualizarFornecedor } from '../hooks/useAtualizarFornecedor'
import { useInativarFornecedor } from '../hooks/useInativarFornecedor'

export function FornecedorDetalhePage() {
  const { fornecedorId } = useParams<{ fornecedorId: string }>()
  const { data: fornecedor, isLoading } = useFornecedor(fornecedorId)
  const { mutate: atualizar, isPending } = useAtualizarFornecedor(fornecedorId ?? '')
  const { mutate: inativar } = useInativarFornecedor()

  if (isLoading) {
    return (
      <PageWrapper title="Fornecedor">
        <Spinner label="Carregando fornecedor..." />
      </PageWrapper>
    )
  }

  if (!fornecedor) {
    return (
      <PageWrapper title="Fornecedor">
        <EmptyState title="Fornecedor não encontrado" description="Verifique o endereço ou volte para a lista de fornecedores." />
      </PageWrapper>
    )
  }

  return (
    <PageWrapper title={fornecedor.razao_social} description="Dados cadastrais do fornecedor.">
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Editar dados</CardTitle>
          <div className="flex items-center gap-2">
            <Badge tone={fornecedor.ativo ? 'ok' : 'neutral'}>{fornecedor.ativo ? 'Ativo' : 'Inativo'}</Badge>
            {fornecedor.ativo && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  if (window.confirm(`Inativar o fornecedor ${fornecedor.razao_social}?`)) inativar(fornecedor.id)
                }}
              >
                Inativar
              </Button>
            )}
          </div>
        </CardHeader>
        <FornecedorForm
          defaultValues={fornecedor}
          isSubmitting={isPending}
          submitLabel="Salvar alterações"
          onSubmit={(values) => atualizar(values)}
        />
      </Card>
    </PageWrapper>
  )
}
