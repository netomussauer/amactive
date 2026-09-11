import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Badge } from '@/shared/components/ui/Badge'
import { routes } from '@/shared/lib/routes'
import { ProdutoForm } from '../components/ProdutoForm'
import { MatrizVariantesForm } from '../components/MatrizVariantesForm'
import { useCriarProduto } from '../hooks/useCriarProduto'
import type { Produto } from '../types/produto.types'

// Fluxo de criação de produto em dois passos: 1) dados cadastrais do
// produto, 2) matriz de variantes (cor × tamanho) — não existe endpoint de
// criação em lote no backend, então a matriz é montada e disparada aqui
// (ver hooks/useCriarVariantesEmLote.ts). O passo de variantes pode ser
// pulado e retomado depois em ProdutoDetalhePage.
export function ProdutoNovoPage() {
  const navigate = useNavigate()
  const { mutate, isPending } = useCriarProduto()
  const [produtoCriado, setProdutoCriado] = useState<Produto | null>(null)

  function irParaDetalhe() {
    if (produtoCriado) navigate(routes.produtoDetalhe(produtoCriado.id))
  }

  if (produtoCriado) {
    return (
      <PageWrapper
        title="Cadastrar variantes"
        description={`Monte a matriz de cores e tamanhos de "${produtoCriado.nome}".`}
      >
        <Card className="max-w-4xl">
          <CardHeader>
            <CardTitle>Matriz de variantes (cor × tamanho)</CardTitle>
            <Badge tone="ok">Produto cadastrado</Badge>
          </CardHeader>
          <MatrizVariantesForm
            produtoId={produtoCriado.id}
            nomeProduto={produtoCriado.nome}
            onConcluido={irParaDetalhe}
            onPular={irParaDetalhe}
          />
        </Card>
      </PageWrapper>
    )
  }

  return (
    <PageWrapper title="Novo produto" description="Cadastre um novo produto no catálogo AMACTIVE.">
      <Card className="max-w-2xl">
        <ProdutoForm
          isSubmitting={isPending}
          submitLabel="Cadastrar produto"
          onSubmit={(values) => {
            mutate(values, {
              onSuccess: (produto) => setProdutoCriado(produto),
            })
          }}
        />
      </Card>
    </PageWrapper>
  )
}
