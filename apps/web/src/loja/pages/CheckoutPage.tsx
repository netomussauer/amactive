import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { Textarea } from '@/shared/components/ui/Textarea'
import { FormField } from '@/shared/components/ui/FormField'
import { EmptyState } from '@/shared/components/ui/EmptyState'
import { formatCurrencyBRL } from '@/shared/lib/format'
import { CheckoutFormSchema, type CheckoutFormValues } from '../schemas/checkout.schema'
import { useCriarPedidoLoja } from '../hooks/useLojaQueries'
import { useCarrinhoStore, totalEmCentavos } from '../store/carrinho.store'

export function CheckoutPage() {
  const itens = useCarrinhoStore((estado) => estado.itens)
  const limpar = useCarrinhoStore((estado) => estado.limpar)
  const navigate = useNavigate()
  const criarPedido = useCriarPedidoLoja()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<CheckoutFormValues>({
    resolver: zodResolver(CheckoutFormSchema),
    defaultValues: { nome: '', telefone: '', observacao: '' },
  })

  if (itens.length === 0) {
    return (
      <EmptyState
        title="Nenhuma peça no carrinho"
        description="Adicione peças antes de finalizar o pedido."
        action={
          <Link to="/" className="text-sm font-medium text-primary underline">
            Ver a coleção
          </Link>
        }
      />
    )
  }

  function enviar(valores: CheckoutFormValues) {
    criarPedido.mutate(
      {
        cliente: { nome: valores.nome, telefone: valores.telefone },
        observacao: valores.observacao?.trim() || undefined,
        itens: itens.map((item) => ({ variante_id: item.varianteId, quantidade: item.quantidade })),
      },
      {
        onSuccess: (pedido) => {
          // Navega antes de limpar: evita a tela de "carrinho vazio" piscando.
          navigate('/pedido-enviado', { state: { pedido, nomeCliente: valores.nome.trim() } })
          limpar()
        },
      },
    )
  }

  const total = totalEmCentavos(itens)

  return (
    <div className="grid gap-8 md:grid-cols-[1fr_320px]">
      <section aria-labelledby="titulo-checkout" className="flex flex-col gap-5">
        <h1 id="titulo-checkout" className="font-sans text-2xl font-semibold text-text">
          Seus dados
        </h1>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit(enviar)} noValidate>
          <FormField label="Nome" htmlFor="nome" required error={errors.nome?.message}>
            <Input
              id="nome"
              autoComplete="name"
              invalid={!!errors.nome}
              aria-describedby={errors.nome ? 'nome-error' : undefined}
              {...register('nome')}
            />
          </FormField>
          <FormField
            label="WhatsApp"
            htmlFor="telefone"
            required
            hint="Usamos este número para confirmar o pedido com você."
            error={errors.telefone?.message}
          >
            <Input
              id="telefone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              placeholder="(11) 99999-9999"
              invalid={!!errors.telefone}
              aria-describedby={errors.telefone ? 'telefone-error' : undefined}
              {...register('telefone')}
            />
          </FormField>
          <FormField label="Observação" htmlFor="observacao" error={errors.observacao?.message}>
            <Textarea id="observacao" rows={3} placeholder="Opcional" {...register('observacao')} />
          </FormField>

          <Button type="submit" size="lg" isLoading={criarPedido.isPending}>
            Enviar pedido
          </Button>
          <p className="text-xs text-text-muted">
            Ao enviar, reservamos as peças por um prazo limitado. Você recebe o resumo para enviar pelo WhatsApp e
            combinamos o pagamento por lá.
          </p>
        </form>
      </section>

      <aside aria-label="Resumo do pedido" className="flex h-fit flex-col gap-3 rounded-lg border border-border p-5">
        <h2 className="text-base font-semibold">Resumo</h2>
        <ul className="flex flex-col gap-2 text-sm">
          {itens.map((item) => (
            <li key={item.varianteId} className="flex justify-between gap-2">
              <span className="text-text-muted">
                {item.quantidade}x {item.produtoNome} {item.cor} {item.tamanho}
              </span>
            </li>
          ))}
        </ul>
        <div className="flex items-center justify-between border-t border-border pt-3 font-semibold">
          <span>Total</span>
          <span>{formatCurrencyBRL(total / 100)}</span>
        </div>
      </aside>
    </div>
  )
}
