import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Badge } from '@/shared/components/ui/Badge'
import { Stepper } from '@/shared/components/ui/Stepper'
import { routes } from '@/shared/lib/routes'
import { ProdutoForm } from '../components/ProdutoForm'
import { MatrizVariantesForm } from '../components/MatrizVariantesForm'
import { useCriarProduto } from '../hooks/useCriarProduto'
import { CADASTRO_PRODUTO_STEPS } from '../lib/cadastro-produto-steps'
import type { Produto } from '../types/produto.types'

// Fluxo de criação de produto em dois passos: 1) dados cadastrais do
// produto, 2) matriz de variantes (cor × tamanho) — não existe endpoint de
// criação em lote no backend, então a matriz é montada e disparada aqui
// (ver hooks/useCriarVariantesEmLote.ts). O passo de variantes pode ser
// pulado e retomado depois em ProdutoDetalhePage. Um terceiro passo
// ("Imagens") acontece fisicamente em ProdutoDetalhePage — o Stepper no
// rodapé aqui é só indicativo da jornada completa, não navegável.
export function ProdutoNovoPage() {
  const navigate = useNavigate()
  const { mutate, isPending } = useCriarProduto()
  const [produtoCriado, setProdutoCriado] = useState<Produto | null>(null)

  function irParaDetalhe() {
    if (produtoCriado) {
      // `fromCadastro` sinaliza a ProdutoDetalhePage que o usuário veio do
      // fluxo de criação, para exibir o passo 3 ("Imagens") do Stepper —
      // não aparece quando alguém simplesmente abre um produto já existente.
      navigate(routes.produtoDetalhe(produtoCriado.id), { state: { fromCadastro: true } })
    }
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
        <Stepper steps={CADASTRO_PRODUTO_STEPS} currentStepId="variantes" className="mx-auto mt-8 max-w-4xl" />
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
      <Stepper steps={CADASTRO_PRODUTO_STEPS} currentStepId="dados" className="mx-auto mt-8 max-w-2xl" />
    </PageWrapper>
  )
}
