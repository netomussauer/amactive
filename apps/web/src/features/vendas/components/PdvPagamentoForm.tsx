import { useEffect, useMemo, useRef, useState } from 'react'
import { useFieldArray, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Select } from '@/shared/components/ui/Select'
import { FormField } from '@/shared/components/ui/FormField'
import { Textarea } from '@/shared/components/ui/Textarea'
import { formatCurrencyBRL, toDecimalString } from '@/shared/lib/format'
import { getErrorMessage } from '@/shared/lib/get-error-message'
import { ApiError } from '@/shared/lib/api-client'
import {
  FormaPagamentoSchema,
  validarOrigemCanal,
  type OrigemCanal,
  type PagamentoRequest,
  type PedidoDetalhe,
} from '../schemas/pedido.schema'
import { useCarrinhoStore } from '../store/carrinho.store'
import { useCriarPedido } from '../hooks/useCriarPedido'
import { labelCanal, labelPedidoExterno } from '../lib/canal'

const PagamentoFormBaseSchema = z.object({
  desconto: z.string().regex(/^\d+\.\d{2}$/, 'Use o formato 0.00'),
  observacao: z.string().optional(),
  pedido_externo_id: z.string().max(100, 'Máximo de 100 caracteres').optional(),
  pagamentos: z
    .array(
      z.object({
        forma_pagamento: FormaPagamentoSchema,
        valor: z.string().regex(/^\d+(\.\d{1,2})?$/, 'Informe um valor válido'),
      }),
    )
    .min(1, 'Informe ao menos uma forma de pagamento'),
})
type PagamentoFormValues = z.infer<typeof PagamentoFormBaseSchema>

// As regras por canal (NUVEMSHOP exige número; PDV e WHATSAPP não têm) vêm do mesmo
// validador usado em CriarPedidoSchema — o erro aparece inline antes do POST.
function criarPagamentoFormSchema(origemCanal: OrigemCanal) {
  return PagamentoFormBaseSchema.superRefine((values, ctx) =>
    validarOrigemCanal({ origem_canal: origemCanal, pedido_externo_id: values.pedido_externo_id }, ctx),
  )
}

// NUVEMSHOP não aparece aqui de propósito: só é usada (fixa) no canal Nuvemshop.
const formasPagamento: Array<{ value: PagamentoRequest['forma_pagamento']; label: string }> = [
  { value: 'DINHEIRO', label: 'Dinheiro' },
  { value: 'PIX', label: 'PIX' },
  { value: 'CARTAO_DEBITO', label: 'Cartão de débito' },
  { value: 'CARTAO_CREDITO', label: 'Cartão de crédito' },
]

function pagamentosIniciais(origemCanal: OrigemCanal, total: number): PagamentoFormValues['pagamentos'] {
  return [
    {
      forma_pagamento: origemCanal === 'NUVEMSHOP' ? 'NUVEMSHOP' : 'DINHEIRO',
      valor: toDecimalString(total),
    },
  ]
}

type Props = {
  subtotal: number
  onConfirmado: (pedido: PedidoDetalhe) => void
}

export function PdvPagamentoForm({ subtotal, onConfirmado }: Props) {
  const itens = useCarrinhoStore((state) => state.itens)
  const clienteId = useCarrinhoStore((state) => state.clienteId)
  const origemCanal = useCarrinhoStore((state) => state.origemCanal)
  const [somaDivergente, setSomaDivergente] = useState(false)

  const { mutate, isPending, error } = useCriarPedido()

  const resolverSchema = useMemo(() => criarPagamentoFormSchema(origemCanal), [origemCanal])

  const {
    register,
    control,
    handleSubmit,
    setValue,
    setError,
    clearErrors,
    formState: { errors },
  } = useForm<PagamentoFormValues>({
    resolver: zodResolver(resolverSchema),
    defaultValues: {
      desconto: '0.00',
      observacao: '',
      pedido_externo_id: '',
      pagamentos: pagamentosIniciais(origemCanal, subtotal),
    },
  })

  const { fields, append, remove, replace } = useFieldArray({ control, name: 'pagamentos' })
  const pagamentosAtuais = useWatch({ control, name: 'pagamentos' })
  const desconto = useWatch({ control, name: 'desconto' })

  const totalComDesconto = useMemo(() => Math.max(0, subtotal - Number(desconto || 0)), [subtotal, desconto])
  const isNuvemshop = origemCanal === 'NUVEMSHOP'
  // Nuvemshop: pagamento fixo = total (o cliente já pagou no checkout do canal).
  const somaPagamentos = useMemo(
    () =>
      isNuvemshop
        ? totalComDesconto
        : pagamentosAtuais.reduce((acc, pagamento) => acc + Number(pagamento.valor || 0), 0),
    [isNuvemshop, totalComDesconto, pagamentosAtuais],
  )
  const diferenca = Number((totalComDesconto - somaPagamentos).toFixed(2))

  // Trocar de canal invalida o que foi lançado para o canal anterior: o número do
  // pedido externo é limpo, erros/avisos somem e, ao cruzar a fronteira Nuvemshop
  // (entrar ou sair), os pagamentos voltam ao padrão do novo canal — NUVEMSHOP só
  // existe no canal Nuvemshop, nunca nos demais. Entre PDV e WhatsApp os pagamentos
  // já lançados continuam válidos e são mantidos. Carrinho, cliente, desconto e
  // observação nunca são tocados. Sincroniza o store (fonte externa) com o form —
  // único uso legítimo de efeito aqui.
  const canalAnterior = useRef(origemCanal)
  useEffect(() => {
    if (canalAnterior.current === origemCanal) return
    const cruzouNuvemshop = (canalAnterior.current === 'NUVEMSHOP') !== (origemCanal === 'NUVEMSHOP')
    canalAnterior.current = origemCanal
    if (cruzouNuvemshop) replace(pagamentosIniciais(origemCanal, totalComDesconto))
    setValue('pedido_externo_id', '')
    clearErrors()
    setSomaDivergente(false)
  }, [origemCanal, totalComDesconto, replace, setValue, clearErrors])

  function handleConfirmarVenda(values: PagamentoFormValues) {
    if (!isNuvemshop && diferenca !== 0) {
      setSomaDivergente(true)
      return
    }
    setSomaDivergente(false)

    // Só a Nuvemshop envia número; PDV e WHATSAPP nunca (o backend responde 422).
    const pedidoExternoId = isNuvemshop ? (values.pedido_externo_id ?? '').trim() : ''
    const pagamentos: PagamentoRequest[] = isNuvemshop
      ? [{ forma_pagamento: 'NUVEMSHOP', valor: totalComDesconto.toFixed(2) }]
      : values.pagamentos.map((pagamento) => ({
          forma_pagamento: pagamento.forma_pagamento,
          valor: Number(pagamento.valor).toFixed(2),
        }))

    mutate(
      {
        cliente_id: clienteId,
        origem_canal: origemCanal,
        ...(pedidoExternoId ? { pedido_externo_id: pedidoExternoId } : {}),
        desconto: values.desconto,
        observacao: values.observacao,
        itens: itens.map((item) => ({
          variante_id: item.varianteId,
          quantidade: item.quantidade,
          desconto_item: item.descontoItem,
        })),
        pagamentos,
      },
      {
        onSuccess: onConfirmado,
        onError: (err) => {
          // 409: já existe pedido da Nuvemshop com esse número. O carrinho (store) e o
          // form permanecem intactos; só marca o campo para o operador corrigir.
          if (err instanceof ApiError && err.status === 409 && isNuvemshop) {
            setError('pedido_externo_id', {
              type: 'server',
              message: `Já existe um pedido ${labelCanal(origemCanal)} com o número ${pedidoExternoId}.`,
            })
          }
        },
      },
    )
  }

  const estoqueInsuficiente = error instanceof ApiError && error.status === 422
  const conflitoNumero = isNuvemshop && error instanceof ApiError && error.status === 409

  return (
    <form className="space-y-4" onSubmit={handleSubmit(handleConfirmarVenda)} noValidate>
      {/* Só a Nuvemshop tem número de pedido externo (obrigatório). */}
      {isNuvemshop && (
        <FormField
          label={labelPedidoExterno(origemCanal)}
          htmlFor="pedido-externo-id"
          required
          error={errors.pedido_externo_id?.message}
        >
          <Input
            id="pedido-externo-id"
            autoComplete="off"
            aria-required="true"
            invalid={Boolean(errors.pedido_externo_id)}
            aria-describedby={errors.pedido_externo_id ? 'pedido-externo-id-error' : undefined}
            placeholder="Ex: 1024"
            {...register('pedido_externo_id')}
          />
        </FormField>
      )}

      {origemCanal === 'WHATSAPP' && (
        <p className="rounded-md bg-bg-subtle p-3 text-xs text-text-muted">
          Vendas do WhatsApp não usam número de pedido. Para identificar a cliente, use o seletor de cliente no
          carrinho e o campo Observação.
        </p>
      )}

      <FormField label="Desconto no pedido" htmlFor="desconto" error={errors.desconto?.message}>
        <Input id="desconto" placeholder="0.00" {...register('desconto')} />
      </FormField>

      {isNuvemshop ? (
        <div className="rounded-md border border-border bg-bg-subtle p-3 text-sm">
          <span className="font-medium text-text">Forma de pagamento</span>
          <p className="mt-1 text-text-muted">
            Pago externamente pelo checkout da Nuvemshop — {formatCurrencyBRL(totalComDesconto)}
          </p>
        </div>
      ) : (
        <div>
          <div className="mb-2 flex items-center justify-between">
            <span className="text-sm font-medium text-text">Formas de pagamento</span>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => append({ forma_pagamento: 'DINHEIRO', valor: '0.00' })}
            >
              <Plus className="h-3.5 w-3.5" aria-hidden="true" />
              Adicionar forma
            </Button>
          </div>

          <div className="space-y-2">
            {fields.map((field, index) => (
              <div key={field.id} className="flex items-center gap-2">
                <Select
                  aria-label={`Forma de pagamento ${index + 1}`}
                  className="flex-1"
                  {...register(`pagamentos.${index}.forma_pagamento` as const)}
                >
                  {formasPagamento.map((forma) => (
                    <option key={forma.value} value={forma.value}>
                      {forma.label}
                    </option>
                  ))}
                </Select>
                <Input
                  aria-label={`Valor da forma de pagamento ${index + 1}`}
                  className="w-28"
                  placeholder="0.00"
                  {...register(`pagamentos.${index}.valor` as const)}
                />
                {fields.length > 1 && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label="Remover forma de pagamento"
                    onClick={() => remove(index)}
                  >
                    <Trash2 className="h-4 w-4 text-danger" aria-hidden="true" />
                  </Button>
                )}
              </div>
            ))}
          </div>
          {errors.pagamentos?.message && (
            <p role="alert" className="mt-1 text-xs text-danger">
              {errors.pagamentos.message}
            </p>
          )}
        </div>
      )}

      <FormField label="Observação (opcional)" htmlFor="observacao">
        <Textarea id="observacao" placeholder="Ex: cliente pediu troca em 5 dias" {...register('observacao')} />
      </FormField>

      <div className="space-y-1 rounded-md bg-bg-subtle p-3 text-sm">
        <div className="flex justify-between">
          <span className="text-text-muted">Subtotal</span>
          <span>{formatCurrencyBRL(subtotal)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-text-muted">Desconto</span>
          <span>- {formatCurrencyBRL(desconto || '0.00')}</span>
        </div>
        <div className="flex justify-between font-sans text-base font-bold text-text">
          <span>Total a pagar</span>
          <span>{formatCurrencyBRL(totalComDesconto)}</span>
        </div>
        <div className="flex justify-between text-text-muted">
          <span>Total informado nos pagamentos</span>
          <span>{formatCurrencyBRL(somaPagamentos)}</span>
        </div>
      </div>

      {somaDivergente && (
        <p role="alert" className="rounded-md border border-danger bg-bg p-2.5 text-sm text-danger">
          A soma dos pagamentos ({formatCurrencyBRL(somaPagamentos)}) precisa ser igual ao total a pagar (
          {formatCurrencyBRL(totalComDesconto)}). Ajuste os valores para continuar.
        </p>
      )}

      {error && !conflitoNumero && (
        <p role="alert" className="rounded-md border border-danger bg-bg p-2.5 text-sm text-danger">
          {estoqueInsuficiente
            ? 'Estoque insuficiente para um ou mais itens do carrinho. Ajuste as quantidades no carrinho e tente novamente.'
            : getErrorMessage(error)}
        </p>
      )}

      <Button type="submit" className="w-full" isLoading={isPending} aria-busy={isPending} disabled={itens.length === 0}>
        {isPending ? 'Confirmando venda...' : 'Confirmar venda'}
      </Button>
    </form>
  )
}
