"""Implementação concreta dos Protocols de `domain/repositories.py` sobre os
modelos de `models.py`.

`SqlAlchemyCredencialCanalRepository` (`CredencialCanalRepository`) foi
implementada no passo 5 (ver docs/design-integracao-nuvemshop.md §9) — é o
adaptador que alimenta `client.py` com o token/secret decifrados.
`SqlAlchemyWebhookEventoRepository`/`SqlAlchemyMapeamentoVarianteRepository`
são implementadas no passo 6 (webhook/mapeamento), usadas pelo controller de
webhook e por `ProcessarWebhookPedidoUseCase`.
`SqlAlchemyIntegracaoEstoqueOutboxRepository` é implementada no passo 7
(outbox de estoque, design §4), usada por `PublicarEstoqueCanalUseCase`.
`SqlAlchemyIntegracaoCatalogoOutboxRepository` é implementada no passo 8
(outbox de catálogo, design §4/§2.4), usada por
`PublicarCatalogoCanalUseCase` — mesma forma exata de
`SqlAlchemyIntegracaoEstoqueOutboxRepository`, chave `produto_id`.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import RowMapping, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.integracao_canais.domain.entities import (
    CanalIntegracao,
    IntegracaoCatalogoOutbox,
    IntegracaoEstoqueOutbox,
    MapeamentoVarianteCanal,
    OperacaoCatalogoOutbox,
    StatusOutbox,
    StatusWebhookEvento,
    WebhookEvento,
)
from amactive.contexts.integracao_canais.domain.repositories import CredencialDecifrada
from amactive.contexts.integracao_canais.infrastructure.metrics import (
    webhook_evento_conflito_manual_total,
)
from amactive.contexts.integracao_canais.infrastructure.persistence.models import (
    IntegracaoCatalogoOutboxModel,
    IntegracaoEstoqueOutboxModel,
    MapeamentoVarianteCanalModel,
    WebhookEventoModel,
)
from amactive.core.config import settings


def _now() -> datetime:
    return datetime.now(UTC)


class SqlAlchemyCredencialCanalRepository:
    """Implementa `CredencialCanalRepository` (design §2.5/§7.2) — decifra
    `access_token_cifrado`/`client_secret_cifrado` via `pgp_sym_decrypt`
    (extensão `pgcrypto`, já habilitada no banco desde
    `migrations/000001_initial_schema` — nenhuma dependência Python de
    criptografia é introduzida por este repositório).

    A chave de cifragem (`Settings.credencial_canal_encryption_key`) nunca
    é interpolada na string SQL — sempre passada como bind parameter
    (`:chave`), e nunca aparece em log/exceção deste módulo."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def buscar_token_decifrado(self, canal: CanalIntegracao) -> CredencialDecifrada | None:
        resultado = await self._session.execute(
            text(
                """
                SELECT
                    store_id,
                    pgp_sym_decrypt(access_token_cifrado, :chave) AS access_token,
                    pgp_sym_decrypt(client_secret_cifrado, :chave) AS client_secret
                FROM credencial_canal
                WHERE canal = :canal
                """
            ),
            {"chave": settings.credencial_canal_encryption_key, "canal": canal.value},
        )
        linha = resultado.mappings().first()
        if linha is None:
            return None
        return CredencialDecifrada(
            canal=canal,
            store_id=linha["store_id"],
            access_token=linha["access_token"],
            client_secret=linha["client_secret"],
        )


class SqlAlchemyWebhookEventoRepository:
    """Implementa `WebhookEventoRepository` (design §2.5/§5.1-§5.3)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def registrar_se_novo(
        self,
        *,
        canal: CanalIntegracao,
        tipo_evento: str,
        id_recurso_externo: str,
        payload_bruto: dict,
    ) -> WebhookEvento | None:
        # Construído aqui (não no chamador) — é este INSERT que de fato
        # precisa do valor para o ON CONFLICT (evento_externo_id); ver
        # invariante documentada em domain/entities.py (WebhookEvento).
        evento_externo_id = f"{canal.value}:{tipo_evento}:{id_recurso_externo}"
        insert_stmt = pg_insert(WebhookEventoModel).values(
            id=uuid4(),
            canal=canal.value,
            evento_externo_id=evento_externo_id,
            tipo_evento=tipo_evento,
            id_recurso_externo=id_recurso_externo,
            payload_bruto=payload_bruto,
            status=StatusWebhookEvento.PENDENTE.value,
            tentativas=0,
            erro_detalhe=None,
            recebido_em=_now(),
            processado_em=None,
        )
        stmt = insert_stmt.on_conflict_do_nothing(
            index_elements=[WebhookEventoModel.evento_externo_id]
        ).returning(
            WebhookEventoModel.id,
            WebhookEventoModel.canal,
            WebhookEventoModel.evento_externo_id,
            WebhookEventoModel.tipo_evento,
            WebhookEventoModel.id_recurso_externo,
            WebhookEventoModel.payload_bruto,
            WebhookEventoModel.status,
            WebhookEventoModel.tentativas,
            WebhookEventoModel.erro_detalhe,
            WebhookEventoModel.recebido_em,
            WebhookEventoModel.processado_em,
        )
        resultado = await self._session.execute(stmt)
        linha = resultado.mappings().first()
        await self._session.flush()
        if linha is None:
            # ON CONFLICT DO NOTHING não inseriu nada — evento duplicado
            # (design §5.1/§5.2), não é erro.
            return None
        return _webhook_evento_linha_para_entidade(linha)

    async def buscar_lote_pendente(self, *, limite: int) -> list[WebhookEvento]:
        resultado = await self._session.execute(
            select(WebhookEventoModel)
            .where(
                WebhookEventoModel.status.in_(
                    [StatusWebhookEvento.PENDENTE.value, StatusWebhookEvento.ERRO.value]
                )
            )
            .order_by(WebhookEventoModel.recebido_em)
            .limit(limite)
            # SKIP LOCKED — permite múltiplas réplicas do worker sem
            # duplicar processamento (design §4.2/§9, mesmo mecanismo do
            # coalescing dos outbox).
            .with_for_update(skip_locked=True)
        )
        return [_webhook_evento_modelo_para_entidade(m) for m in resultado.scalars().all()]

    async def marcar_processado(self, evento_id: UUID) -> None:
        modelo = await self._session.get(WebhookEventoModel, evento_id)
        if modelo is None:
            return
        modelo.status = StatusWebhookEvento.PROCESSADO.value
        modelo.processado_em = _now()
        await self._session.flush()

    async def marcar_erro(self, evento_id: UUID, *, detalhe: str) -> None:
        modelo = await self._session.get(WebhookEventoModel, evento_id)
        if modelo is None:
            return
        modelo.status = StatusWebhookEvento.ERRO.value
        modelo.tentativas += 1
        modelo.erro_detalhe = detalhe
        await self._session.flush()

    async def marcar_conflito_manual(self, evento_id: UUID, *, detalhe: str) -> None:
        modelo = await self._session.get(WebhookEventoModel, evento_id)
        if modelo is None:
            return
        modelo.status = StatusWebhookEvento.CONFLITO_MANUAL.value
        modelo.erro_detalhe = detalhe
        await self._session.flush()
        # Métrica `webhook_evento_conflito_manual_total` (design §5.4/§8) —
        # único ponto de gravação de CONFLITO_MANUAL do sistema (todos os
        # chamadores de `ProcessarWebhookPedidoUseCase` passam por aqui),
        # então incrementar neste repositório cobre todo motivo de conflito
        # sem precisar duplicar a chamada em cada ponto de uso.
        webhook_evento_conflito_manual_total.inc()


class SqlAlchemyMapeamentoVarianteRepository:
    """Implementa `MapeamentoVarianteRepository` (design §2.5/§2.4/§6.3)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def buscar_por_variante_externo(
        self, *, canal: CanalIntegracao, variante_externo_id: str
    ) -> MapeamentoVarianteCanal | None:
        resultado = await self._session.execute(
            select(MapeamentoVarianteCanalModel).where(
                MapeamentoVarianteCanalModel.canal == canal.value,
                MapeamentoVarianteCanalModel.variante_externo_id == variante_externo_id,
            )
        )
        modelo = resultado.scalar_one_or_none()
        return _mapeamento_para_entidade(modelo) if modelo else None

    async def buscar_por_variante_id(
        self, *, variante_id: UUID, canal: CanalIntegracao
    ) -> MapeamentoVarianteCanal | None:
        resultado = await self._session.execute(
            select(MapeamentoVarianteCanalModel).where(
                MapeamentoVarianteCanalModel.variante_id == variante_id,
                MapeamentoVarianteCanalModel.canal == canal.value,
            )
        )
        modelo = resultado.scalar_one_or_none()
        return _mapeamento_para_entidade(modelo) if modelo else None

    async def upsert(
        self,
        *,
        variante_id: UUID,
        canal: CanalIntegracao,
        produto_externo_id: str,
        variante_externo_id: str,
    ) -> MapeamentoVarianteCanal:
        agora = _now()
        insert_stmt = pg_insert(MapeamentoVarianteCanalModel).values(
            id=uuid4(),
            variante_id=variante_id,
            canal=canal.value,
            produto_externo_id=produto_externo_id,
            variante_externo_id=variante_externo_id,
            criado_em=agora,
            atualizado_em=None,
        )
        stmt = insert_stmt.on_conflict_do_update(
            # `uq_mapeamento_variante_canal UNIQUE (variante_id, canal)`
            # — uma variante AMACTIVE tem no máximo um mapeamento por
            # canal (design §2.4/§6.3); a primeira publicação cria, uma
            # republicação atualiza os IDs externos no lugar.
            index_elements=[
                MapeamentoVarianteCanalModel.variante_id,
                MapeamentoVarianteCanalModel.canal,
            ],
            set_={
                "produto_externo_id": insert_stmt.excluded.produto_externo_id,
                "variante_externo_id": insert_stmt.excluded.variante_externo_id,
                "atualizado_em": agora,
            },
        ).returning(
            MapeamentoVarianteCanalModel.id,
            MapeamentoVarianteCanalModel.variante_id,
            MapeamentoVarianteCanalModel.canal,
            MapeamentoVarianteCanalModel.produto_externo_id,
            MapeamentoVarianteCanalModel.variante_externo_id,
            MapeamentoVarianteCanalModel.criado_em,
            MapeamentoVarianteCanalModel.atualizado_em,
        )
        resultado = await self._session.execute(stmt)
        linha = resultado.mappings().one()
        await self._session.flush()
        return MapeamentoVarianteCanal(
            id=linha["id"],
            variante_id=linha["variante_id"],
            canal=CanalIntegracao(linha["canal"]),
            produto_externo_id=linha["produto_externo_id"],
            variante_externo_id=linha["variante_externo_id"],
            criado_em=linha["criado_em"],
            atualizado_em=linha["atualizado_em"],
        )


class SqlAlchemyIntegracaoEstoqueOutboxRepository:
    """Implementa `IntegracaoEstoqueOutboxRepository` (design §2.5/§4.2/§4.3)
    — consumida por `PublicarEstoqueCanalUseCase` (passo 7)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def buscar_lote_pendente_coalescido(
        self, *, limite: int
    ) -> list[IntegracaoEstoqueOutbox]:
        # Coalescing de design §4.2 — só a linha mais recente por
        # `variante_id` importa (o valor publicado é sempre o saldo
        # absoluto atual, nunca um delta). `FOR UPDATE SKIP LOCKED` permite
        # múltiplas réplicas do worker sem duplicar processamento.
        #
        # Desvio deliberado da forma EXATA da query de design §4.2 (que
        # combina `SELECT DISTINCT ON (...) ... FOR UPDATE` num único
        # nível): o Postgres real rejeita essa combinação —
        # `FeatureNotSupportedError: FOR UPDATE is not allowed with
        # DISTINCT clause` (confirmado rodando contra Postgres 16, não é
        # suposição). A subquery em `WHERE id IN (...)` preserva
        # exatamente a mesma semântica (o `DISTINCT ON` roda sem
        # `FOR UPDATE`, só para decidir QUAIS linhas são "a mais recente
        # por variante_id") — só o lock em si (`FOR UPDATE SKIP LOCKED`)
        # se move para a query externa, que enxerga uma única relação
        # (`integracao_estoque_outbox`), sem ambiguidade de qual relação
        # travar.
        resultado = await self._session.execute(
            text(
                """
                SELECT *
                FROM integracao_estoque_outbox
                WHERE id IN (
                    SELECT DISTINCT ON (variante_id) id
                    FROM integracao_estoque_outbox
                    WHERE status IN ('PENDENTE', 'ERRO')
                      AND (proxima_tentativa_em IS NULL OR proxima_tentativa_em <= now())
                    ORDER BY variante_id, criado_em DESC
                )
                ORDER BY criado_em
                LIMIT :limite
                FOR UPDATE SKIP LOCKED
                """
            ),
            {"limite": limite},
        )
        linhas = resultado.mappings().all()
        return [_estoque_outbox_linha_para_entidade(linha) for linha in linhas]

    async def marcar_enviado(self, outbox_id: UUID, *, superseded_ids: list[UUID]) -> None:
        modelo = await self._session.get(IntegracaoEstoqueOutboxModel, outbox_id)
        if modelo is None:
            return

        # Descobre as linhas mais antigas da mesma `variante_id` que
        # ficaram "para trás" (PENDENTE/ERRO) — nunca chegaram a ser
        # publicadas individualmente, mas o estado que representavam já foi
        # superado pela mais recente, que acabou de ser enviada (design
        # §4.2). Esta consulta é a fonte definitiva da verdade: o chamador
        # (`PublicarEstoqueCanalUseCase`) normalmente não tem essa
        # informação, já que `buscar_lote_pendente_coalescido` só retorna a
        # linha mais recente por `variante_id` via `DISTINCT ON` — o
        # parâmetro `superseded_ids` é apenas unido ao resultado, para um
        # chamador futuro que já os conheça de antemão não pagar o custo de
        # uma segunda consulta.
        resultado = await self._session.execute(
            select(IntegracaoEstoqueOutboxModel.id).where(
                IntegracaoEstoqueOutboxModel.variante_id == modelo.variante_id,
                IntegracaoEstoqueOutboxModel.status.in_(
                    [StatusOutbox.PENDENTE.value, StatusOutbox.ERRO.value]
                ),
                IntegracaoEstoqueOutboxModel.id != outbox_id,
            )
        )
        ids_supersededos_descobertos = {linha[0] for linha in resultado.all()}
        todos_os_ids = {outbox_id, *ids_supersededos_descobertos, *superseded_ids}

        await self._session.execute(
            update(IntegracaoEstoqueOutboxModel)
            .where(IntegracaoEstoqueOutboxModel.id.in_(todos_os_ids))
            .values(status=StatusOutbox.ENVIADO.value, processado_em=_now())
        )
        await self._session.flush()

    async def marcar_erro_com_retry(
        self, outbox_id: UUID, *, detalhe: str, proxima_tentativa_em: datetime
    ) -> None:
        modelo = await self._session.get(IntegracaoEstoqueOutboxModel, outbox_id)
        if modelo is None:
            return
        modelo.status = StatusOutbox.ERRO.value
        modelo.tentativas += 1
        modelo.erro_detalhe = detalhe
        modelo.proxima_tentativa_em = proxima_tentativa_em
        await self._session.flush()

    async def contar_pendentes(self) -> int:
        """`SELECT count(*) ... WHERE status IN ('PENDENTE', 'ERRO')` —
        alimenta o gauge `integracao_outbox_pendente{fila="estoque"}`
        (design §8), sem nenhuma query nova além da já necessária."""
        total = await self._session.scalar(
            select(func.count())
            .select_from(IntegracaoEstoqueOutboxModel)
            .where(
                IntegracaoEstoqueOutboxModel.status.in_(
                    [StatusOutbox.PENDENTE.value, StatusOutbox.ERRO.value]
                )
            )
        )
        return int(total or 0)


class SqlAlchemyIntegracaoCatalogoOutboxRepository:
    """Implementa `IntegracaoCatalogoOutboxRepository` (design §2.5/§4.2/§4.3)
    — consumida por `PublicarCatalogoCanalUseCase` (passo 8). Mesma forma
    exata de `SqlAlchemyIntegracaoEstoqueOutboxRepository`, chave
    `produto_id` em vez de `variante_id` — inclusive a mesma correção da
    query de coalescing (Postgres rejeita `SELECT DISTINCT ON (...) FOR
    UPDATE` combinados, ver comentário na consulta abaixo)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def buscar_lote_pendente_coalescido(
        self, *, limite: int
    ) -> list[IntegracaoCatalogoOutbox]:
        # Coalescing de design §4.2 — só a linha mais recente por
        # `produto_id` importa (o valor publicado é sempre o produto
        # completo atual, nunca um delta). `FOR UPDATE SKIP LOCKED` permite
        # múltiplas réplicas do worker sem duplicar processamento.
        #
        # Mesmo desvio deliberado da forma EXATA da query de design §4.2 já
        # aplicado ao outbox de estoque (passo 7): o Postgres real rejeita
        # `SELECT DISTINCT ON (...) ... FOR UPDATE` combinados num único
        # nível — `FeatureNotSupportedError: FOR UPDATE is not allowed with
        # DISTINCT clause` (confirmado rodando contra Postgres 16). A
        # subquery em `WHERE id IN (...)` preserva a mesma semântica.
        resultado = await self._session.execute(
            text(
                """
                SELECT *
                FROM integracao_catalogo_outbox
                WHERE id IN (
                    SELECT DISTINCT ON (produto_id) id
                    FROM integracao_catalogo_outbox
                    WHERE status IN ('PENDENTE', 'ERRO')
                      AND (proxima_tentativa_em IS NULL OR proxima_tentativa_em <= now())
                    ORDER BY produto_id, criado_em DESC
                )
                ORDER BY criado_em
                LIMIT :limite
                FOR UPDATE SKIP LOCKED
                """
            ),
            {"limite": limite},
        )
        linhas = resultado.mappings().all()
        return [_catalogo_outbox_linha_para_entidade(linha) for linha in linhas]

    async def marcar_enviado(self, outbox_id: UUID, *, superseded_ids: list[UUID]) -> None:
        modelo = await self._session.get(IntegracaoCatalogoOutboxModel, outbox_id)
        if modelo is None:
            return

        # Descobre as linhas mais antigas do mesmo `produto_id` que ficaram
        # "para trás" (PENDENTE/ERRO) — nunca chegaram a ser publicadas
        # individualmente, mas o estado que representavam já foi superado
        # pela mais recente, que acabou de ser enviada (design §4.2). Mesmo
        # raciocínio de `SqlAlchemyIntegracaoEstoqueOutboxRepository.marcar_enviado`.
        resultado = await self._session.execute(
            select(IntegracaoCatalogoOutboxModel.id).where(
                IntegracaoCatalogoOutboxModel.produto_id == modelo.produto_id,
                IntegracaoCatalogoOutboxModel.status.in_(
                    [StatusOutbox.PENDENTE.value, StatusOutbox.ERRO.value]
                ),
                IntegracaoCatalogoOutboxModel.id != outbox_id,
            )
        )
        ids_supersededos_descobertos = {linha[0] for linha in resultado.all()}
        todos_os_ids = {outbox_id, *ids_supersededos_descobertos, *superseded_ids}

        await self._session.execute(
            update(IntegracaoCatalogoOutboxModel)
            .where(IntegracaoCatalogoOutboxModel.id.in_(todos_os_ids))
            .values(status=StatusOutbox.ENVIADO.value, processado_em=_now())
        )
        await self._session.flush()

    async def marcar_erro_com_retry(
        self, outbox_id: UUID, *, detalhe: str, proxima_tentativa_em: datetime
    ) -> None:
        modelo = await self._session.get(IntegracaoCatalogoOutboxModel, outbox_id)
        if modelo is None:
            return
        modelo.status = StatusOutbox.ERRO.value
        modelo.tentativas += 1
        modelo.erro_detalhe = detalhe
        modelo.proxima_tentativa_em = proxima_tentativa_em
        await self._session.flush()

    async def contar_pendentes(self) -> int:
        """Idem `SqlAlchemyIntegracaoEstoqueOutboxRepository.contar_pendentes`,
        para o gauge `integracao_outbox_pendente{fila="catalogo"}`."""
        total = await self._session.scalar(
            select(func.count())
            .select_from(IntegracaoCatalogoOutboxModel)
            .where(
                IntegracaoCatalogoOutboxModel.status.in_(
                    [StatusOutbox.PENDENTE.value, StatusOutbox.ERRO.value]
                )
            )
        )
        return int(total or 0)


def _catalogo_outbox_linha_para_entidade(linha: RowMapping) -> IntegracaoCatalogoOutbox:
    """`linha` vem de `text(...)` com `SELECT *` (não de um `Model` do ORM)
    — mesma razão de `_estoque_outbox_linha_para_entidade`."""
    return IntegracaoCatalogoOutbox(
        id=linha["id"],
        produto_id=linha["produto_id"],
        operacao=OperacaoCatalogoOutbox(linha["operacao"]),
        status=StatusOutbox(linha["status"]),
        tentativas=linha["tentativas"],
        proxima_tentativa_em=linha["proxima_tentativa_em"],
        erro_detalhe=linha["erro_detalhe"],
        criado_em=linha["criado_em"],
        processado_em=linha["processado_em"],
    )


def _estoque_outbox_linha_para_entidade(linha: RowMapping) -> IntegracaoEstoqueOutbox:
    """`linha` vem de `text(...)` com `SELECT *` (não de um `Model` do ORM)
    — a query de coalescing de §4.2 é SQL puro, por isso o acesso é por
    nome de coluna via `.mappings()`, mesmo padrão de
    `_webhook_evento_linha_para_entidade`."""
    return IntegracaoEstoqueOutbox(
        id=linha["id"],
        variante_id=linha["variante_id"],
        quantidade_publicada=linha["quantidade_publicada"],
        status=StatusOutbox(linha["status"]),
        tentativas=linha["tentativas"],
        proxima_tentativa_em=linha["proxima_tentativa_em"],
        erro_detalhe=linha["erro_detalhe"],
        criado_em=linha["criado_em"],
        processado_em=linha["processado_em"],
    )


def _webhook_evento_linha_para_entidade(linha: RowMapping) -> WebhookEvento:
    """`linha` vem do `.returning(...)` de `registrar_se_novo` — colunas
    explícitas via `.mappings()` (mesmo padrão de
    `cadastros/infrastructure/persistence/repositories.py`,
    `upsert_por_email`), nunca o `WebhookEventoModel` inteiro."""
    return WebhookEvento(
        id=linha["id"],
        canal=CanalIntegracao(linha["canal"]),
        evento_externo_id=linha["evento_externo_id"],
        tipo_evento=linha["tipo_evento"],
        id_recurso_externo=linha["id_recurso_externo"],
        payload_bruto=linha["payload_bruto"],
        status=StatusWebhookEvento(linha["status"]),
        tentativas=linha["tentativas"],
        erro_detalhe=linha["erro_detalhe"],
        recebido_em=linha["recebido_em"],
        processado_em=linha["processado_em"],
    )


def _webhook_evento_modelo_para_entidade(modelo: WebhookEventoModel) -> WebhookEvento:
    return WebhookEvento(
        id=modelo.id,
        canal=CanalIntegracao(modelo.canal),
        evento_externo_id=modelo.evento_externo_id,
        tipo_evento=modelo.tipo_evento,
        id_recurso_externo=modelo.id_recurso_externo,
        payload_bruto=modelo.payload_bruto,
        status=StatusWebhookEvento(modelo.status),
        tentativas=modelo.tentativas,
        erro_detalhe=modelo.erro_detalhe,
        recebido_em=modelo.recebido_em,
        processado_em=modelo.processado_em,
    )


def _mapeamento_para_entidade(modelo: MapeamentoVarianteCanalModel) -> MapeamentoVarianteCanal:
    return MapeamentoVarianteCanal(
        id=modelo.id,
        variante_id=modelo.variante_id,
        canal=CanalIntegracao(modelo.canal),
        produto_externo_id=modelo.produto_externo_id,
        variante_externo_id=modelo.variante_externo_id,
        criado_em=modelo.criado_em,
        atualizado_em=modelo.atualizado_em,
    )
