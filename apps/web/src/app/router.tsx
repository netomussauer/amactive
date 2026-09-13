import { lazy, Suspense, type ReactNode } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AuthGuard } from './AuthGuard'
import { RoleGuard } from './RoleGuard'
import { RootRedirect } from './RootRedirect'
import { AuthLayout } from '@/shared/components/layout/AuthLayout'
import { Spinner } from '@/shared/components/ui/Spinner'
import { routes } from '@/shared/lib/routes'
import type { Permissoes } from '@/shared/lib/permissoes'

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
const UsuariosListPage = lazy(() =>
  import('@/features/usuarios/pages/UsuariosListPage').then((m) => ({ default: m.UsuariosListPage })),
)
const UsuarioNovoPage = lazy(() =>
  import('@/features/usuarios/pages/UsuarioNovoPage').then((m) => ({ default: m.UsuarioNovoPage })),
)
const UsuarioDetalhePage = lazy(() =>
  import('@/features/usuarios/pages/UsuarioDetalhePage').then((m) => ({ default: m.UsuarioDetalhePage })),
)

// Fallback exibido pelo Suspense enquanto o chunk da página carrega.
function PageFallback() {
  return <Spinner label="Carregando página…" />
}

function withSuspense(element: React.ReactNode) {
  return <Suspense fallback={<PageFallback />}>{element}</Suspense>
}

// Combina o guard de papel (RBAC, ver app/RoleGuard.tsx) com o Suspense do
// code-splitting por rota. Usado nas páginas cujo acesso completo — não só
// ações de escrita — é restrito a um subconjunto de papéis.
function withRole(permissao: keyof Permissoes, element: ReactNode) {
  return withSuspense(<RoleGuard permissao={permissao}>{element}</RoleGuard>)
}

export const router = createBrowserRouter([
  { path: '/', element: <AuthGuard><RootRedirect /></AuthGuard> },
  { path: routes.login, element: withSuspense(<LoginPage />) },
  {
    element: (
      <AuthGuard>
        <AuthLayout />
      </AuthGuard>
    ),
    children: [
      // Dashboard/Relatórios — leitura restrita a ADMIN (ver docs/openapi.yaml, x-roles: [ADMIN]).
      { path: routes.dashboard, element: withRole('podeVerRelatorios', <DashboardPage />) },
      { path: routes.relatorios, element: withRole('podeVerRelatorios', <RelatoriosPage />) },

      // Produtos/Estoque — leitura livre aos três papéis; ações de escrita
      // são condicionadas inline dentro de cada página/componente (ver
      // shared/hooks/usePermissoes.ts). "Novo produto" é a exceção: é uma
      // página só de escrita, então o guard cobre a rota inteira.
      { path: routes.produtos, element: withSuspense(<ProdutosListPage />) },
      { path: routes.produtoNovo, element: withRole('podeGerenciarCatalogo', <ProdutoNovoPage />) },
      { path: '/produtos/:produtoId', element: withSuspense(<ProdutoDetalhePage />) },
      { path: routes.estoque, element: withSuspense(<EstoquePage />) },
      { path: routes.estoqueMovimentacoes, element: withSuspense(<MovimentacoesPage />) },

      // PDV — página inteira é o fluxo de criar pedido; ESTOQUISTA não pode
      // nem abri-la (leitura de Pedidos continua livre, ver rotas abaixo).
      { path: routes.pdv, element: withRole('podeVenderNoPdv', <PdvPage />) },
      { path: routes.pedidos, element: withSuspense(<PedidosListPage />) },
      { path: '/vendas/pedidos/:pedidoId', element: withSuspense(<PedidoDetalhePage />) },

      // Clientes — ESTOQUISTA não tem leitura alguma do recurso (ver
      // docs/openapi.yaml, x-roles: [ADMIN, VENDEDOR]) — guarda a rota inteira.
      { path: routes.clientes, element: withRole('podeGerenciarClientes', <ClientesListPage />) },
      { path: routes.clienteNovo, element: withRole('podeGerenciarClientes', <ClienteNovoPage />) },
      { path: '/clientes/:clienteId', element: withRole('podeGerenciarClientes', <ClienteDetalhePage />) },

      // Fornecedores — VENDEDOR não tem leitura alguma do recurso (ver
      // docs/openapi.yaml, x-roles: [ADMIN, ESTOQUISTA]) — guarda a rota inteira.
      { path: routes.fornecedores, element: withRole('podeGerenciarFornecedores', <FornecedoresListPage />) },
      { path: routes.fornecedorNovo, element: withRole('podeGerenciarFornecedores', <FornecedorNovoPage />) },
      {
        path: '/fornecedores/:fornecedorId',
        element: withRole('podeGerenciarFornecedores', <FornecedorDetalhePage />),
      },

      // Usuários — CRUD administrativo, restrito a ADMIN (ver
      // docs/openapi.yaml, tag "Usuários", x-roles: [ADMIN] em toda a
      // subárvore) — guarda a rota inteira, mesmo padrão de Clientes/Fornecedores.
      { path: routes.usuarios, element: withRole('podeGerenciarUsuarios', <UsuariosListPage />) },
      { path: routes.usuarioNovo, element: withRole('podeGerenciarUsuarios', <UsuarioNovoPage />) },
      { path: '/usuarios/:usuarioId', element: withRole('podeGerenciarUsuarios', <UsuarioDetalhePage />) },
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
