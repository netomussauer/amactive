import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import { Button } from '@/shared/components/ui/Button'
import { Input } from '@/shared/components/ui/Input'
import { FormField } from '@/shared/components/ui/FormField'
import { useAuth } from '@/shared/hooks/useAuth'
import { routes } from '@/shared/lib/routes'
import { getErrorMessage } from '@/shared/lib/get-error-message'
import { LoginFormSchema, type LoginFormValues } from '../schemas/auth.schema'
import { useLogin } from '../hooks/useLogin'

export function LoginPage() {
  const isAuthenticated = useAuth((state) => state.isAuthenticated)
  const navigate = useNavigate()
  const location = useLocation()
  const { mutate, isPending, error } = useLogin()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(LoginFormSchema),
    defaultValues: { email: '', senha: '' },
  })

  if (isAuthenticated) {
    const redirectTo = (location.state as { from?: string } | null)?.from ?? routes.dashboard
    return <Navigate to={redirectTo} replace />
  }

  function handleLogin(values: LoginFormValues) {
    mutate(values, {
      onSuccess: () => {
        const redirectTo = (location.state as { from?: string } | null)?.from ?? routes.dashboard
        navigate(redirectTo, { replace: true })
      },
    })
  }

  return (
    <div className="flex min-h-screen">
      <div className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-graphite-900 p-12 text-white lg:flex">
        <div className="absolute inset-0 bg-gradient-to-br from-coral-600 via-graphite-900 to-graphite-900" />
        <div className="relative z-10 font-sans text-2xl font-bold tracking-tight">AMACTIVE</div>
        <div className="relative z-10 max-w-sm">
          <Sparkles className="mb-4 h-8 w-8 text-coral-400" aria-hidden="true" />
          <h2 className="font-sans text-3xl font-bold leading-tight">
            Moda fitness feminina, controle total do balcão ao estoque.
          </h2>
          <p className="mt-3 text-sm text-graphite-200">
            Gerencie produtos, estoque e vendas em um só lugar — feito para o ritmo da loja.
          </p>
        </div>
        <p className="relative z-10 text-xs text-graphite-200">© {new Date().getFullYear()} AMACTIVE</p>
      </div>

      <div className="flex w-full flex-1 items-center justify-center bg-bg px-6 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">
          <h1 className="font-sans text-2xl font-bold text-text lg:hidden">AMACTIVE</h1>
          <h1 className="mt-2 font-sans text-2xl font-bold text-text">Entrar</h1>
          <p className="mt-1 text-sm text-text-muted">Acesse o painel de estoque e vendas.</p>

          <form className="mt-8 space-y-4" onSubmit={handleSubmit(handleLogin)} noValidate>
            <FormField label="E-mail" htmlFor="email" required error={errors.email?.message}>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="voce@amactive.dev"
                invalid={Boolean(errors.email)}
                aria-required="true"
                aria-describedby={errors.email ? 'email-error' : undefined}
                {...register('email')}
              />
            </FormField>

            <FormField label="Senha" htmlFor="senha" required error={errors.senha?.message}>
              <Input
                id="senha"
                type="password"
                autoComplete="current-password"
                placeholder="••••••••"
                invalid={Boolean(errors.senha)}
                aria-required="true"
                aria-describedby={errors.senha ? 'senha-error' : undefined}
                {...register('senha')}
              />
            </FormField>

            {error && (
              <p role="alert" className="rounded-md border border-danger bg-bg p-2.5 text-sm text-danger">
                {getErrorMessage(error)}
              </p>
            )}

            <Button type="submit" className="w-full" isLoading={isPending} aria-busy={isPending}>
              {isPending ? 'Entrando...' : 'Entrar'}
            </Button>
          </form>

          <p className="mt-6 text-xs text-text-muted">
            Ambiente de desenvolvimento: <strong>admin@amactive.dev</strong> / <strong>amactive123</strong>
          </p>
        </div>
      </div>
    </div>
  )
}
