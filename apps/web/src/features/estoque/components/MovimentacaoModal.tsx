import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Search } from 'lucide-react'
import { Modal } from '@/shared/components/ui/Modal'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Select } from '@/shared/components/ui/Select'
import { FormField } from '@/shared/components/ui/FormField'
import { Badge } from '@/shared/components/ui/Badge'
import { useDebounce } from '@/shared/hooks/useDebounce'
import { useProdutoPorSku } from '@/features/produtos'
import { useFornecedores } from '@/features/fornecedores'
import { CriarMovimentacaoSchema, type CriarMovimentacaoDTO } from '../schemas/movimentacao.schema'
import { useCriarMovimentacao } from '../hooks/useCriarMovimentacao'

type Props = {
  open: boolean
  onClose: () => void
}

// Modal de registro manual de movimentação de estoque (entrada/saída/ajuste).
export function MovimentacaoModal({ open, onClose }: Props) {
  const [skuInput, setSkuInput] = useState('')
  const skuDebounced = useDebounce(skuInput)
  const { data: resultado, isFetching } = useProdutoPorSku(skuDebounced, open)
  const { data: fornecedores } = useFornecedores({ per_page: 100 })
  const { mutate, isPending, error } = useCriarMovimentacao()

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    watch,
    formState: { errors },
  } = useForm<CriarMovimentacaoDTO>({
    resolver: zodResolver(CriarMovimentacaoSchema),
    defaultValues: { variante_id: '', tipo: 'ENTRADA', quantidade: 1, motivo: 'COMPRA', fornecedor_id: null },
  })

  const motivo = watch('motivo')

  useEffect(() => {
    if (resultado?.variante) setValue('variante_id', resultado.variante.id, { shouldValidate: true })
  }, [resultado, setValue])

  useEffect(() => {
    if (!open) {
      setSkuInput('')
      reset()
    }
  }, [open, reset])

  function handleClose() {
    onClose()
  }

  function handleFormSubmit(values: CriarMovimentacaoDTO) {
    mutate(values, { onSuccess: handleClose })
  }

  return (
    <Modal open={open} onClose={handleClose} title="Nova movimentação de estoque">
      <div className="space-y-4">
        <FormField label="Buscar variante por SKU" htmlFor="sku-busca" hint="Digite o SKU exato do produto">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" aria-hidden="true" />
            <Input
              id="sku-busca"
              className="pl-9"
              placeholder="LEG-CORAL-M"
              value={skuInput}
              onChange={(event) => setSkuInput(event.target.value)}
            />
          </div>
        </FormField>

        {isFetching && <p className="text-sm text-text-muted">Buscando...</p>}
        {!isFetching && skuDebounced && !resultado && (
          <p role="alert" className="text-sm text-danger">
            Nenhuma variante encontrada para o SKU informado.
          </p>
        )}
        {resultado && (
          <div className="rounded-md border border-border bg-bg-subtle p-3 text-sm">
            <p className="font-medium text-text">
              {resultado.produtoNome} — {resultado.variante.tamanho}/{resultado.variante.cor}
            </p>
            <p className="mt-1 text-text-muted">
              SKU {resultado.variante.sku} · Estoque atual: <Badge tone="neutral">{resultado.variante.quantidade_estoque}</Badge>
            </p>
          </div>
        )}

        <form className="space-y-4" onSubmit={handleSubmit(handleFormSubmit)} noValidate>
          <div className="grid grid-cols-2 gap-4">
            <FormField label="Tipo" htmlFor="tipo" required error={errors.tipo?.message}>
              <Select id="tipo" {...register('tipo')}>
                <option value="ENTRADA">Entrada</option>
                <option value="SAIDA">Saída</option>
                <option value="AJUSTE">Ajuste</option>
              </Select>
            </FormField>

            <FormField label="Quantidade" htmlFor="quantidade" required error={errors.quantidade?.message}>
              <Input
                id="quantidade"
                type="number"
                min={1}
                invalid={Boolean(errors.quantidade)}
                aria-required="true"
                {...register('quantidade', { valueAsNumber: true })}
              />
            </FormField>
          </div>

          <FormField label="Motivo" htmlFor="motivo" required error={errors.motivo?.message}>
            <Select id="motivo" {...register('motivo')}>
              <option value="COMPRA">Compra</option>
              <option value="AJUSTE_INVENTARIO">Ajuste de inventário</option>
              <option value="DEVOLUCAO">Devolução</option>
              <option value="PERDA">Perda</option>
            </Select>
          </FormField>

          {motivo === 'COMPRA' && (
            <FormField label="Fornecedor" htmlFor="fornecedor_id" error={errors.fornecedor_id?.message}>
              <Select
                id="fornecedor_id"
                {...register('fornecedor_id', { setValueAs: (value: string) => (value === '' ? null : value) })}
              >
                <option value="">Não informado</option>
                {fornecedores?.data.map((fornecedor) => (
                  <option key={fornecedor.id} value={fornecedor.id}>
                    {fornecedor.razao_social}
                  </option>
                ))}
              </Select>
            </FormField>
          )}

          {errors.variante_id && (
            <p role="alert" className="text-sm text-danger">
              Busque e selecione uma variante válida antes de continuar.
            </p>
          )}

          {error && (
            <p role="alert" className="rounded-md border border-danger bg-bg p-2.5 text-sm text-danger">
              Não foi possível registrar a movimentação. Verifique o saldo disponível e tente novamente.
            </p>
          )}

          <Button
            type="submit"
            className="w-full"
            isLoading={isPending}
            aria-busy={isPending}
            disabled={!resultado}
          >
            {isPending ? 'Registrando...' : 'Registrar movimentação'}
          </Button>
        </form>
      </div>
    </Modal>
  )
}
