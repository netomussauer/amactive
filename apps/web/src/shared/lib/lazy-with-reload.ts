import { lazy, type ComponentType } from 'react'

// Envolve `React.lazy` para sobreviver a um redeploy: o bundle principal já
// carregado no navegador referencia os chunks de cada rota pelo nome com hash
// (ex.: ProdutoDetalhePage-BvoQ2H-t.js) gerado NA BUILD em que a aba foi
// aberta. Cada novo deploy publica hashes novos e o Kaniko não preserva os
// arquivos antigos — se o usuário navega para uma rota ainda não visitada
// nessa aba DEPOIS de um deploy, o import() dinâmico tenta buscar um arquivo
// que já não existe mais e falha com "Failed to fetch dynamically imported
// module" (TypeError, sem fallback do React), quebrando a página inteira.
//
// Sem sessionStorage não seria seguro só recarregar sempre no catch: uma
// falha de rede genuína (não relacionada a deploy) entraria em loop de
// reload. A flag garante no máximo UMA tentativa de recarregamento por aba;
// se voltar a falhar depois do reload, o erro é propagado normalmente (cai
// no ErrorBoundary/Suspense mais próximo).
const CHAVE_RECARREGADO = 'amactive:chunk-reload-attempted'

export function lazyWithReload<T extends { default: ComponentType<unknown> }>(
  factory: () => Promise<T>,
) {
  return lazy(async () => {
    try {
      const modulo = await factory()
      // Import bem-sucedido: qualquer tentativa de recovery anterior já
      // resolveu o problema — libera uma nova tentativa se um deploy futuro
      // causar o mesmo erro mais tarde nesta mesma aba.
      sessionStorage.removeItem(CHAVE_RECARREGADO)
      return modulo
    } catch (error) {
      const jaTentouRecarregar = sessionStorage.getItem(CHAVE_RECARREGADO) === '1'
      if (!jaTentouRecarregar) {
        sessionStorage.setItem(CHAVE_RECARREGADO, '1')
        window.location.reload()
        // A navegação real acontece de forma assíncrona — devolve uma
        // Promise que nunca resolve para o Suspense continuar mostrando o
        // fallback de carregamento até o reload de fato ocorrer, em vez de
        // seguir tentando renderizar com o módulo ausente.
        return new Promise<never>(() => {})
      }
      throw error
    }
  })
}
