import { createBrowserRouter } from 'react-router-dom'

// Scaffold de rotas — o dev-expert-front deve substituir a rota placeholder
// abaixo pelas páginas reais de cada feature (ver docs/frontend-architecture.md
// §4 para o sitemap completo: /login, /dashboard, /produtos, /estoque,
// /vendas/pdv, /vendas/pedidos, /clientes, /fornecedores, /relatorios).
export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <main className="flex min-h-screen items-center justify-center bg-bg-subtle">
        <div className="rounded-lg bg-white p-8 shadow-md">
          <h1 className="font-sans text-2xl text-primary">AMACTIVE</h1>
          <p className="mt-2 text-text-muted">
            Scaffold de arquitetura — telas ainda não implementadas.
          </p>
        </div>
      </main>
    ),
  },
])
