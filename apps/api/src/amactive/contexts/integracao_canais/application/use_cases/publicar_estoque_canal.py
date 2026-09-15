"""Command — usado pelo worker (`run_worker.py`).

Implementa `PublicarEstoqueCanalUseCase` (design
docs/design-integracao-nuvemshop.md §4, especialmente §4.2 — coalescing — e
§4.3 — idempotência/retry): consome
`IntegracaoEstoqueOutboxRepository.buscar_lote_pendente_coalescido` e
publica o saldo absoluto de cada variante via
`NuvemshopClientPort.atualizar_estoque_variante`.

Decisão documentada — item de outbox sem `MapeamentoVarianteCanal` ainda
(design §9 passo 7, deixado em aberto pelo design para este passo decidir):
a variante nunca foi publicada na Nuvemshop (o outbox de catálogo, passo 8,
ainda não criou o mapeamento na primeira publicação). Não há produto/variante
externa para atualizar hoje — a opção mais simples e correta é marcar a
linha como `ENVIADO` mesmo assim (não é uma falha; é "nada a fazer ainda"),
em vez de deixá-la reprocessando indefinidamente em `PENDENTE`/`ERRO` até o
outbox de catálogo publicar o produto. Quando o passo 8 publicar o produto
pela primeira vez, ele publica o estoque *atual* como parte do payload de
criação (a Nuvemshop aninha variantes no recurso de produto) — este outbox
de estoque não precisa "esperar" o mapeamento aparecer para ficar
consistente.

Retry/backoff (design §4.3): política compartilhada com o outbox de
catálogo, extraída para `_backoff_outbox.py` — ver docstring daquele módulo
para o detalhamento completo (backoff exponencial + jitter, teto de
tentativas, tratamento de 4xx vs. 5xx/429, e a nota técnica sobre a
sentinela `SEM_REPROCESSAMENTO_AUTOMATICO`)."""

from __future__ import annotations

from typing import Final

from amactive.contexts.integracao_canais.application.use_cases._backoff_outbox import (
    calcular_proxima_tentativa_em,
)
from amactive.contexts.integracao_canais.domain.entities import (
    CanalIntegracao,
    IntegracaoEstoqueOutbox,
)
from amactive.contexts.integracao_canais.domain.exceptions import NuvemshopIndisponivel
from amactive.contexts.integracao_canais.domain.repositories import (
    IntegracaoEstoqueOutboxRepository,
    MapeamentoVarianteRepository,
    NuvemshopClientPort,
)

# Tamanho de lote pequeno de propósito (design §4.5, "processa um lote
# pequeno a cada tick") — o rate limiter da Nuvemshop (2 req/s) já é o
# limitador real de throughput, não o tamanho do lote lido do banco.
LIMITE_LOTE_PADRAO: Final = 20


class PublicarEstoqueCanalUseCase:
    """Ver docstring do módulo."""

    def __init__(
        self,
        *,
        nuvemshop_client: NuvemshopClientPort,
        mapeamento_variante_repository: MapeamentoVarianteRepository,
        outbox_repository: IntegracaoEstoqueOutboxRepository,
    ) -> None:
        self._nuvemshop = nuvemshop_client
        self._mapeamentos = mapeamento_variante_repository
        self._outbox = outbox_repository

    async def executar(self, *, limite: int = LIMITE_LOTE_PADRAO) -> int:
        """Processa um lote coalescido de `integracao_estoque_outbox`
        (design §4.2) — chamado a cada tick por `run_worker.py`. Retorna a
        quantidade de linhas "líder" processadas (cada uma pode ter
        marcado 0+ linhas supersededas adicionais como `ENVIADO`) — usado
        pelo worker apenas para logging básico do tick."""
        lote = await self._outbox.buscar_lote_pendente_coalescido(limite=limite)
        for item in lote:
            await self._processar_item(item)
        return len(lote)

    async def _processar_item(self, item: IntegracaoEstoqueOutbox) -> None:
        mapeamento = await self._mapeamentos.buscar_por_variante_id(
            variante_id=item.variante_id, canal=CanalIntegracao.NUVEMSHOP
        )
        if mapeamento is None:
            # Ver decisão documentada no docstring do módulo — nada a
            # publicar ainda, não é uma falha.
            await self._outbox.marcar_enviado(item.id, superseded_ids=[])
            return

        try:
            await self._nuvemshop.atualizar_estoque_variante(
                produto_externo_id=mapeamento.produto_externo_id,
                variante_externo_id=mapeamento.variante_externo_id,
                quantidade=item.quantidade_publicada,
            )
        except NuvemshopIndisponivel as exc:
            await self._tratar_falha(item, exc)
            return

        await self._outbox.marcar_enviado(item.id, superseded_ids=[])

    async def _tratar_falha(
        self, item: IntegracaoEstoqueOutbox, exc: NuvemshopIndisponivel
    ) -> None:
        detalhe = str(exc)
        tentativas_apos_esta_falha = item.tentativas + 1
        proxima_tentativa_em = calcular_proxima_tentativa_em(
            tentativas_apos_esta_falha=tentativas_apos_esta_falha, exc=exc
        )
        await self._outbox.marcar_erro_com_retry(
            item.id, detalhe=detalhe, proxima_tentativa_em=proxima_tentativa_em
        )
