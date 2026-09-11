import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { PageWrapper } from '@/shared/components/layout/PageWrapper'
import { Badge } from '@/shared/components/ui/Badge'
import { Button } from '@/shared/components/ui/Button'
import { Card, CardHeader, CardTitle } from '@/shared/components/ui/Card'
import { Modal } from '@/shared/components/ui/Modal'
import { Table, TableHead, TableBody, TableRow, TableHeadCell, TableCell } from '@/shared/components/ui/Table'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { Spinner } from '@/shared/components/ui/Spinner'
import { formatCurrencyBRL } from '@/shared/lib/format'
import { ProdutoCard } from '../components/ProdutoCard'
import { ProdutoForm } from '../components/ProdutoForm'
import { VarianteForm } from '../components/VarianteForm'
import { GaleriaImagensProduto } from '../components/GaleriaImagensProduto'
import { useProduto } from '../hooks/useProduto'
import { useAtualizarProduto } from '../hooks/useAtualizarProduto'
import { useCriarVariante } from '../hooks/useCriarVariante'
import { useInativarVariante } from '../hooks/useInativarVariante'

// Detalhe do produto: dados cadastrais + variantes (SKUs).
export function ProdutoDetalhePage() {
  const { produtoId } = useParams<{ produtoId: string }>()
  const [isEditing, setIsEditing] = useState(false)
  const [isVarianteModalOpen, setIsVarianteModalOpen] = useState(false)

  const { data: produto, isLoading } = useProduto(produtoId)
  const { mutate: atualizarProduto, isPending: isUpdating } = useAtualizarProduto(produtoId ?? '')
  const { mutate: criarVariante, isPending: isCreatingVariante } = useCriarVariante(produtoId ?? '')
  const { mutate: inativarVariante } = useInativarVariante(produtoId ?? '')

  if (isLoading) {
    return (
      <PageWrapper title="Produto">
        <Spinner label="Carregando produto..." />
      </PageWrapper>
    )
  }

  if (!produto) {
    return (
      <PageWrapper title="Produto">
        <EmptyState title="Produto não encontrado" description="Verifique o endereço ou volte para a lista de produtos." />
      </PageWrapper>
    )
  }

  return (
    <PageWrapper
      title={produto.nome}
      description="Detalhe do produto e suas variantes (SKUs)."
      actions={
        <Button variant="outline" onClick={() => setIsEditing((prev) => !prev)}>
          {isEditing ? 'Cancelar edição' : 'Editar produto'}
        </Button>
      }
    >
      <div className="space-y-6">
        {isEditing ? (
          <Card className="max-w-2xl">
            <CardHeader>
              <CardTitle>Editar produto</CardTitle>
            </CardHeader>
            <ProdutoForm
              defaultValues={{
                nome: produto.nome,
                descricao: produto.descricao ?? '',
                categoria_id: produto.categoria_id ?? null,
                marca: produto.marca,
              }}
              isSubmitting={isUpdating}
              submitLabel="Salvar alterações"
              onSubmit={(values) => atualizarProduto(values, { onSuccess: () => setIsEditing(false) })}
            />
          </Card>
        ) : (
          <ProdutoCard produto={produto} />
        )}

        <Card>
          <CardHeader>
            <CardTitle>Variantes (SKUs)</CardTitle>
            <Button size="sm" onClick={() => setIsVarianteModalOpen(true)}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              Nova variante
            </Button>
          </CardHeader>

          {produto.variantes.length === 0 ? (
            <EmptyState
              title="Nenhuma variante cadastrada"
              description="Cadastre tamanhos e cores para começar a vender este produto."
            />
          ) : (
            <Table aria-label={`Variantes de ${produto.nome}`}>
              <TableHead>
                <TableRow>
                  <TableHeadCell>SKU</TableHeadCell>
                  <TableHeadCell>Tamanho</TableHeadCell>
                  <TableHeadCell>Cor</TableHeadCell>
                  <TableHeadCell>Preço</TableHeadCell>
                  <TableHeadCell>Estoque</TableHeadCell>
                  <TableHeadCell>Status</TableHeadCell>
                  <TableHeadCell className="text-right">Ações</TableHeadCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {produto.variantes.map((variante) => (
                  <TableRow key={variante.id}>
                    <TableCell className="font-mono text-xs">{variante.sku}</TableCell>
                    <TableCell>{variante.tamanho}</TableCell>
                    <TableCell>{variante.cor}</TableCell>
                    <TableCell>{formatCurrencyBRL(variante.preco_venda)}</TableCell>
                    <TableCell>{variante.quantidade_estoque}</TableCell>
                    <TableCell>
                      <Badge tone={variante.ativo ? 'ok' : 'neutral'}>{variante.ativo ? 'Ativa' : 'Inativa'}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      {variante.ativo && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => {
                            if (window.confirm(`Inativar a variante ${variante.sku}?`)) {
                              inativarVariante(variante.id)
                            }
                          }}
                        >
                          Inativar
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Card>

        <GaleriaImagensProduto
          produtoId={produto.id}
          coresAtivas={Array.from(new Set(produto.variantes.filter((v) => v.ativo).map((v) => v.cor)))}
        />
      </div>

      <Modal open={isVarianteModalOpen} onClose={() => setIsVarianteModalOpen(false)} title="Nova variante (SKU)">
        <VarianteForm
          isSubmitting={isCreatingVariante}
          onSubmit={(values) =>
            criarVariante(values, { onSuccess: () => setIsVarianteModalOpen(false) })
          }
        />
      </Modal>
    </PageWrapper>
  )
}
