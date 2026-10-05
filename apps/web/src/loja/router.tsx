import { createBrowserRouter } from 'react-router-dom'
import { LojaLayout } from './layout/LojaLayout'
import { CatalogoPage } from './pages/CatalogoPage'
import { ProdutoPage } from './pages/ProdutoPage'
import { CarrinhoPage } from './pages/CarrinhoPage'
import { CheckoutPage } from './pages/CheckoutPage'
import { PedidoEnviadoPage } from './pages/PedidoEnviadoPage'

// Rotas da vitrine. Todas públicas — não há AuthGuard nesta aplicação.
export const lojaRouter = createBrowserRouter([
  {
    element: <LojaLayout />,
    children: [
      { path: '/', element: <CatalogoPage /> },
      { path: '/produtos/:produtoId', element: <ProdutoPage /> },
      { path: '/carrinho', element: <CarrinhoPage /> },
      { path: '/finalizar', element: <CheckoutPage /> },
      { path: '/pedido-enviado', element: <PedidoEnviadoPage /> },
    ],
  },
])
