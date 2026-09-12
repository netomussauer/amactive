import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '@/shared/hooks/useAuth'
import { getPermissoes, primeiraRotaPermitida, type Permissoes } from '@/shared/lib/permissoes'

type Props = {
  /** Flag de shared/lib/permissoes.ts exigida para acessar a rota inteira. */
  permissao: keyof Permissoes
  children: ReactNode
}

// Guard de rota por papel (RBAC). Roda dentro do AuthGuard (que já garante
// autenticação) e protege páginas cujo acesso é restrito a um subconjunto de
// papéis por inteiro — não apenas ações de escrita dentro delas. Ex: PDV
// (ESTOQUISTA não pode nem abrir a tela, já que a página inteira é o fluxo
// de criar pedido), Clientes (sem leitura para ESTOQUISTA), Fornecedores
// (sem leitura para VENDEDOR), Dashboard/Relatórios (só ADMIN).
//
// Produtos, Estoque e Pedidos NÃO usam este guard: a leitura desses recursos
// é livre aos três papéis, então a página em si é acessível a todos — só as
// ações de escrita dentro dela são condicionadas inline (ver componentes de
// cada feature, ex: ProdutoDetalhePage, MovimentacoesPage).
//
// Isso evita que o usuário veja uma tela quebrada ao tentar chamar a API a
// partir de uma página fora do seu papel (a tela nem chega a montar); a
// resposta 403 da API continua tratada globalmente como rede de segurança
// (ver shared/lib/get-error-message.ts e shared/lib/query-client.ts) para
// qualquer ação de escrita que porventura não esteja coberta por um guard ou
// por uma checagem inline.
export function RoleGuard({ permissao, children }: Props) {
  const papel = useAuth((state) => state.user?.papel)
  const permissoes = getPermissoes(papel)

  if (!permissoes[permissao]) {
    return <Navigate to={primeiraRotaPermitida(papel)} replace />
  }

  return <>{children}</>
}
