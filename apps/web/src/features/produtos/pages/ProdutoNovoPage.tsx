import { useNavigate } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card } from '@/shared/components/ui/Card'
import { routes } from '@/shared/lib/routes'
import { ProdutoForm } from '../components/ProdutoForm'
import { useCriarProduto } from '../hooks/useCriarProduto'

export function ProdutoNovoPage() {
  const navigate = useNavigate()
  const { mutate, isPending } = useCriarProduto()

  return (
    <PageWrapper title="Novo produto" description="Cadastre um novo produto no catálogo AMACTIVE.">
      <Card className="max-w-2xl">
        <ProdutoForm
          isSubmitting={isPending}
          submitLabel="Cadastrar produto"
          onSubmit={(values) => {
            mutate(values, {
              onSuccess: (produto) => navigate(routes.produtoDetalhe(produto.id)),
            })
          }}
        />
      </Card>
    </PageWrapper>
  )
}
