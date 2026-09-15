"""Command — usado pelo worker (`run_worker.py`).

Implementa `PublicarCatalogoCanalUseCase` (design
docs/design-integracao-nuvemshop.md §4, especialmente §2.4 — granularidade
por produto, não por variante — e §4.2/§4.3 — coalescing e retry): consome
`IntegracaoCatalogoOutboxRepository.buscar_lote_pendente_coalescido`, monta
`ProdutoParaPublicacao` via `CatalogoIntegracaoPort` e cria/atualiza o
produto via `NuvemshopClientPort`, populando/atualizando
`MapeamentoVarianteCanal` para cada variante publicada.

Decisão de design — como decidir entre "primeira publicação" (`criar_produto`)
e "atualização" (`atualizar_produto`): **não** se confia no campo `operacao`
gravado na própria linha de outbox pelo trigger (`CRIAR`/`ATUALIZAR`, ver
migration `000005`) — aquele valor reflete apenas qual evento de banco
enfileirou a linha (`INSERT`/`UPDATE ON produto`), não se o produto já foi
publicado na Nuvemshop. Em vez disso, a fonte da verdade é a existência de
`MapeamentoVarianteCanal` para qualquer variante do produto: se **nenhuma**
variante tem mapeamento, é a primeira publicação; se **pelo menos uma** tem,
é uma atualização usando o `produto_externo_id` já mapeado (mesmo que uma
variante nova tenha sido adicionada depois da primeira publicação — nesse
caso ela ainda não tem mapeamento, mas o produto como um todo já tem).

Retry/backoff (design §4.3): política compartilhada com o outbox de
estoque, extraída para `_backoff_outbox.py` — ver docstring daquele módulo
para o detalhamento completo.
"""

from __future__ import annotations

from typing import Final

from amactive.contexts.integracao_canais.application.use_cases._backoff_outbox import (
    calcular_proxima_tentativa_em,
)
from amactive.contexts.integracao_canais.domain.entities import (
    CanalIntegracao,
    IntegracaoCatalogoOutbox,
)
from amactive.contexts.integracao_canais.domain.exceptions import NuvemshopIndisponivel
from amactive.contexts.integracao_canais.domain.repositories import (
    CatalogoIntegracaoPort,
    IntegracaoCatalogoOutboxRepository,
    MapeamentoVarianteRepository,
    NuvemshopClientPort,
    ProdutoParaPublicacao,
    PublicacaoResultado,
)

# Tamanho de lote pequeno de propósito (design §4.5, "processa um lote
# pequeno a cada tick") — o rate limiter da Nuvemshop (2 req/s) já é o
# limitador real de throughput, não o tamanho do lote lido do banco.
LIMITE_LOTE_PADRAO: Final = 20


class PublicarCatalogoCanalUseCase:
    """Ver docstring do módulo."""

    def __init__(
        self,
        *,
        nuvemshop_client: NuvemshopClientPort,
        catalogo_integracao_port: CatalogoIntegracaoPort,
        mapeamento_variante_repository: MapeamentoVarianteRepository,
        outbox_repository: IntegracaoCatalogoOutboxRepository,
    ) -> None:
        self._nuvemshop = nuvemshop_client
        self._catalogo = catalogo_integracao_port
        self._mapeamentos = mapeamento_variante_repository
        self._outbox = outbox_repository

    async def executar(self, *, limite: int = LIMITE_LOTE_PADRAO) -> int:
        """Processa um lote coalescido de `integracao_catalogo_outbox`
        (design §4.2) — chamado a cada tick por `run_worker.py`. Retorna a
        quantidade de linhas "líder" processadas (cada uma pode ter
        marcado 0+ linhas supersededas adicionais como `ENVIADO`) — usado
        pelo worker apenas para logging básico do tick."""
        lote = await self._outbox.buscar_lote_pendente_coalescido(limite=limite)
        for item in lote:
            await self._processar_item(item)
        return len(lote)

    async def _processar_item(self, item: IntegracaoCatalogoOutbox) -> None:
        produto = await self._catalogo.buscar_produto_para_publicacao(item.produto_id)

        produto_externo_id_ja_mapeado = await self._resolver_produto_externo_id(produto)

        try:
            if produto_externo_id_ja_mapeado is None:
                resultado = await self._nuvemshop.criar_produto(produto)
            else:
                resultado = await self._nuvemshop.atualizar_produto(
                    produto_externo_id_ja_mapeado, produto
                )
        except NuvemshopIndisponivel as exc:
            await self._tratar_falha(item, exc)
            return

        await self._atualizar_mapeamentos(produto, resultado)
        await self._outbox.marcar_enviado(item.id, superseded_ids=[])

    async def _resolver_produto_externo_id(self, produto: ProdutoParaPublicacao) -> str | None:
        """Retorna o `produto_externo_id` já mapeado (uma atualização), ou
        `None` se nenhuma variante do produto tem mapeamento ainda (a
        primeira publicação) — ver decisão documentada no docstring do
        módulo. Uma consulta por variante do produto, mesma forma pedida
        pelo design deste passo."""
        for variante in produto.variantes:
            mapeamento = await self._mapeamentos.buscar_por_variante_id(
                variante_id=variante.variante_id, canal=CanalIntegracao.NUVEMSHOP
            )
            if mapeamento is not None:
                return mapeamento.produto_externo_id
        return None

    async def _atualizar_mapeamentos(
        self, produto: ProdutoParaPublicacao, resultado: PublicacaoResultado
    ) -> None:
        """Cria/atualiza `MapeamentoVarianteCanal` para cada variante do
        produto presente em `resultado.variantes_externo_id` — cobre tanto
        a primeira publicação (todas as variantes são novas) quanto uma
        atualização em que uma variante nova apareceu desde a última
        publicação (o `upsert` é idempotente, então uma variante já mapeada
        simplesmente tem seus IDs externos confirmados/atualizados)."""
        for variante in produto.variantes:
            variante_externo_id = resultado.variantes_externo_id.get(str(variante.variante_id))
            if variante_externo_id is None:
                # Defensivo: não deveria acontecer (o client sempre casa por
                # SKU, e toda variante enviada é esperada na resposta), mas
                # não deve impedir o mapeamento das demais variantes do
                # mesmo produto caso aconteça.
                continue
            await self._mapeamentos.upsert(
                variante_id=variante.variante_id,
                canal=CanalIntegracao.NUVEMSHOP,
                produto_externo_id=resultado.produto_externo_id,
                variante_externo_id=variante_externo_id,
            )

    async def _tratar_falha(
        self, item: IntegracaoCatalogoOutbox, exc: NuvemshopIndisponivel
    ) -> None:
        detalhe = str(exc)
        tentativas_apos_esta_falha = item.tentativas + 1
        proxima_tentativa_em = calcular_proxima_tentativa_em(
            tentativas_apos_esta_falha=tentativas_apos_esta_falha, exc=exc
        )
        await self._outbox.marcar_erro_com_retry(
            item.id, detalhe=detalhe, proxima_tentativa_em=proxima_tentativa_em
        )
