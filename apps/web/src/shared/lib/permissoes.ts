// Regras de RBAC do frontend — espelham a matriz de autorização por papel
// implementada no backend (ver docs/openapi.yaml, seção RBAC em
// `info.description` e a extensão `x-roles` de cada operação). Fonte única
// de verdade para checagens de permissão no frontend: nunca compare
// `papel === 'ADMIN'` (ou similar) diretamente em componentes — use as flags
// abaixo, normalmente via `usePermissoes` (shared/hooks/usePermissoes.ts).
//
// Qualquer mudança na matriz do backend precisa ser replicada aqui.
import { PapelUsuario } from '@/shared/types/api.types'
import { routes } from './routes'

export type Permissoes = {
  /**
   * Produtos/Variantes/Categorias/Imagens — criar, editar e excluir
   * (inativar). Leitura é livre aos três papéis autenticados e não é
   * modelada aqui — ver x-roles de listarProdutos/obterProduto etc.
   */
  podeGerenciarCatalogo: boolean
  /**
   * Estoque — registrar movimentação manual (entrada/saída/ajuste). Leitura
   * de saldo/alertas/histórico é livre aos três papéis.
   */
  podeRegistrarMovimentacaoEstoque: boolean
  /**
   * Vendas/PDV — criar pedido (tela de PDV) e cancelar pedido. Leitura de
   * pedidos (lista/detalhe) é livre aos três papéis.
   */
  podeVenderNoPdv: boolean
  /**
   * Clientes — ver, criar e editar. ESTOQUISTA não tem acesso algum a este
   * recurso, nem leitura (ver x-roles de listarClientes/obterCliente).
   */
  podeGerenciarClientes: boolean
  /**
   * Fornecedores — ver, criar e editar. VENDEDOR não tem acesso algum a
   * este recurso, nem leitura (ver x-roles de listarFornecedores/obterFornecedor).
   */
  podeGerenciarFornecedores: boolean
  /** Dashboard e Relatórios (Vendas por período, Produtos mais vendidos, Giro de estoque) — restrito a ADMIN. */
  podeVerRelatorios: boolean
}

const PERMISSOES_SEM_ACESSO: Permissoes = {
  podeGerenciarCatalogo: false,
  podeRegistrarMovimentacaoEstoque: false,
  podeVenderNoPdv: false,
  podeGerenciarClientes: false,
  podeGerenciarFornecedores: false,
  podeVerRelatorios: false,
}

const PERMISSOES_POR_PAPEL: Record<PapelUsuario, Permissoes> = {
  [PapelUsuario.ADMIN]: {
    podeGerenciarCatalogo: true,
    podeRegistrarMovimentacaoEstoque: true,
    podeVenderNoPdv: true,
    podeGerenciarClientes: true,
    podeGerenciarFornecedores: true,
    podeVerRelatorios: true,
  },
  [PapelUsuario.VENDEDOR]: {
    podeGerenciarCatalogo: false,
    podeRegistrarMovimentacaoEstoque: false,
    podeVenderNoPdv: true,
    podeGerenciarClientes: true,
    podeGerenciarFornecedores: false,
    podeVerRelatorios: false,
  },
  [PapelUsuario.ESTOQUISTA]: {
    podeGerenciarCatalogo: true,
    podeRegistrarMovimentacaoEstoque: true,
    podeVenderNoPdv: false,
    podeGerenciarClientes: false,
    podeGerenciarFornecedores: true,
    podeVerRelatorios: false,
  },
}

/**
 * Resolve as permissões de um papel. `papel` ausente (usuário ainda não
 * carregado ou deslogado) resolve para "nenhuma permissão" — nunca lança.
 */
export function getPermissoes(papel: PapelUsuario | null | undefined): Permissoes {
  if (!papel) return PERMISSOES_SEM_ACESSO
  return PERMISSOES_POR_PAPEL[papel]
}

/**
 * Primeira rota que o papel consegue acessar de fato — usada para
 * redirecionar "/" após o login e como destino de fallback do `RoleGuard`
 * (app/RoleGuard.tsx) quando o usuário tenta abrir uma URL fora do seu
 * papel. Produtos é sempre um destino seguro por último: sua leitura é
 * livre aos três papéis.
 */
export function primeiraRotaPermitida(papel: PapelUsuario | null | undefined): string {
  const permissoes = getPermissoes(papel)
  if (permissoes.podeVerRelatorios) return routes.dashboard
  if (permissoes.podeVenderNoPdv) return routes.pdv
  return routes.produtos
}
