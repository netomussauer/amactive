import { lazy, Suspense } from 'react'
import { createBrowserRouter, Navigate } from 'react-router-dom'
import { AuthGuard } from './AuthGuard'
import { AuthLayout } from '@/shared/components/layout/AuthLayout'
import { Spinner } from '@/shared/components/ui/Spinner'
import { routes } from '@/shared/lib/routes'

// Code splitting por rota — cada página de feature só entra no bundle quando
// a rota é visitada. Ver docs/frontend-architecture.md §6.
const LoginPage = lazy(() => import('@/auth/pages/LoginPage').then((m) => ({ default: m.LoginPage })))
const DashboardPage = lazy(() =>
  import('@/features/dashboard/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const ProdutosListPage = lazy(() =>
  import('@/features/produtos/pages/ProdutosListPage').then((m) => ({ default: m.ProdutosListPage })),
)
const ProdutoNovoPage = lazy(() =>
  import('@/features/produtos/pages/ProdutoNovoPage').then((m) => ({ default: m.ProdutoNovoPage })),
)
const ProdutoDetalhePage = lazy(() =>
  import('@/features/produtos/pages/ProdutoDetalhePage').then((m) => ({ default: m.ProdutoDetalhePage })),
)
const EstoquePage = lazy(() =>
  import('@/features/estoque/pages/EstoquePage').then((m) => ({ default: m.EstoquePage })),
)
const MovimentacoesPage = lazy(() =>
  import('@/features/estoque/pages/MovimentacoesPage').then((m) => ({ default: m.MovimentacoesPage })),
)
const PdvPage = lazy(() => import('@/features/vendas/pages/PdvPage').then((m) => ({ default: m.PdvPage })))
const PedidosListPage = lazy(() =>
  import('@/features/vendas/pages/PedidosListPage').then((m) => ({ default: m.PedidosListPage })),
)
const PedidoDetalhePage = lazy(() =>
  import('@/features/vendas/pages/PedidoDetalhePage').then((m) => ({ default: m.PedidoDetalhePage })),
)
const ClientesListPage = lazy(() =>
  import('@/features/clientes/pages/ClientesListPage').then((m) => ({ default: m.ClientesListPage })),
)
const ClienteNovoPage = lazy(() =>
  import('@/features/clientes/pages/ClienteNovoPage').then((m) => ({ default: m.ClienteNovoPage })),
)
const ClienteDetalhePage = lazy(() =>
  import('@/features/clientes/pages/ClienteDetalhePage').then((m) => ({ default: m.ClienteDetalhePage })),
)
const FornecedoresListPage = lazy(() =>
  import('@/features/fornecedores/pages/FornecedoresListPage').then((m) => ({ default: m.FornecedoresListPage })),
)
const FornecedorNovoPage = lazy(() =>
  import('@/features/fornecedores/pages/FornecedorNovoPage').then((m) => ({ default: m.FornecedorNovoPage })),
)
const FornecedorDetalhePage = lazy(() =>
  import('@/features/fornecedores/pages/FornecedorDetalhePage').then((m) => ({ default: m.FornecedorDetalhePage })),
)
const RelatoriosPage = lazy(() =>
  import('@/features/relatorios/pages/RelatoriosPage').then((m) => ({ default: m.RelatoriosPage })),
)

// Fallback exibido pelo Suspense enquanto o chunk da página carrega.
function PageFallback() {
  return <Spinner label="Carregando página…" />
}

function withSuspense(element: React.ReactNode) {
  return <Suspense fallback={<PageFallback />}>{element}</Suspense>
}

export const router = createBrowserRouter([
  { path: '/', element: <Navigate to={routes.dashboard} replace /> },
  { path: routes.login, element: withSuspense(<LoginPage />) },
  {
    element: (
      <AuthGuard>
        <AuthLayout />
      </AuthGuard>
    ),
    children: [
      { path: routes.dashboard, element: withSuspense(<DashboardPage />) },
      { path: routes.produtos, element: withSuspense(<ProdutosListPage />) },
      { path: routes.produtoNovo, element: withSuspense(<ProdutoNovoPage />) },
      { path: '/produtos/:produtoId', element: withSuspense(<ProdutoDetalhePage />) },
      { path: routes.estoque, element: withSuspense(<EstoquePage />) },
      { path: routes.estoqueMovimentacoes, element: withSuspense(<MovimentacoesPage />) },
      { path: routes.pdv, element: withSuspense(<PdvPage />) },
      { path: routes.pedidos, element: withSuspense(<PedidosListPage />) },
      { path: '/vendas/pedidos/:pedidoId', element: withSuspense(<PedidoDetalhePage />) },
      { path: routes.clientes, element: withSuspense(<ClientesListPage />) },
      { path: routes.clienteNovo, element: withSuspense(<ClienteNovoPage />) },
      { path: '/clientes/:clienteId', element: withSuspense(<ClienteDetalhePage />) },
      { path: routes.fornecedores, element: withSuspense(<FornecedoresListPage />) },
      { path: routes.fornecedorNovo, element: withSuspense(<FornecedorNovoPage />) },
      { path: '/fornecedores/:fornecedorId', element: withSuspense(<FornecedorDetalhePage />) },
      { path: routes.relatorios, element: withSuspense(<RelatoriosPage />) },
    ],
  },
  {
    path: '*',
    element: (
      <main className="flex min-h-screen flex-col items-center justify-center gap-2 bg-bg-subtle text-center">
        <h1 className="font-sans text-2xl font-bold text-text">Página não encontrada</h1>
        <p className="text-text-muted">O endereço acessado não existe.</p>
      </main>
    ),
  },
])
