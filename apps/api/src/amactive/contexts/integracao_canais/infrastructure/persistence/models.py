"""Modelos SQLAlchemy do contexto Integração de Canais — mapeiam
migrations/000005_integracao_nuvemshop.up.sql (seção "Integração de
Canais", ver docs/design-integracao-nuvemshop.md §6.2-§6.6). Nunca usados
para gerar schema (sem `Base.metadata.create_all()` — ver docs/SDD.md
ADR-003).

Implementação dos Protocols de `domain/repositories.py` sobre estes modelos
é passo futuro desta sequência (`infrastructure/persistence/repositories.py`,
passos 6/7/8) — este módulo é só o mapeamento de tabela, sem métodos de
acesso a dados.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import BYTEA, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from amactive.shared_kernel.database import Base
from amactive.shared_kernel.pg_enums import (
    canal_integracao_enum,
    operacao_catalogo_outbox_enum,
    status_outbox_enum,
    status_webhook_evento_enum,
)


class WebhookEventoModel(Base):
    __tablename__ = "webhook_evento"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    canal: Mapped[str] = mapped_column(canal_integracao_enum)
    evento_externo_id: Mapped[str] = mapped_column(String(255), unique=True)
    tipo_evento: Mapped[str] = mapped_column(String(50))
    id_recurso_externo: Mapped[str] = mapped_column(String(100))
    payload_bruto: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(status_webhook_evento_enum)
    tentativas: Mapped[int] = mapped_column(Integer)
    erro_detalhe: Mapped[str | None] = mapped_column(Text)
    recebido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MapeamentoVarianteCanalModel(Base):
    __tablename__ = "mapeamento_variante_canal"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    # ON DELETE RESTRICT: histórico de integração nunca pode ficar órfão,
    # mesmo motivo de item_pedido.variante_id (docs/data-model.md).
    variante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produto_variante.id", ondelete="RESTRICT")
    )
    canal: Mapped[str] = mapped_column(canal_integracao_enum)
    produto_externo_id: Mapped[str] = mapped_column(String(100))
    variante_externo_id: Mapped[str] = mapped_column(String(100))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntegracaoEstoqueOutboxModel(Base):
    __tablename__ = "integracao_estoque_outbox"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    # ON DELETE CASCADE (não RESTRICT): se a variante for fisicamente
    # removida, a fila de publicação associada perde o sentido.
    variante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("produto_variante.id", ondelete="CASCADE")
    )
    quantidade_publicada: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(status_outbox_enum)
    tentativas: Mapped[int] = mapped_column(Integer)
    proxima_tentativa_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    erro_detalhe: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IntegracaoCatalogoOutboxModel(Base):
    __tablename__ = "integracao_catalogo_outbox"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    produto_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("produto.id", ondelete="CASCADE"))
    operacao: Mapped[str] = mapped_column(operacao_catalogo_outbox_enum)
    status: Mapped[str] = mapped_column(status_outbox_enum)
    tentativas: Mapped[int] = mapped_column(Integer)
    proxima_tentativa_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    erro_detalhe: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CredencialCanalModel(Base):
    __tablename__ = "credencial_canal"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    canal: Mapped[str] = mapped_column(canal_integracao_enum, unique=True)
    store_id: Mapped[str] = mapped_column(String(50))
    # Nome deliberado (não "access_token"/"client_secret" sozinhos) — deixa
    # explícito que o valor nunca é texto puro, ver design §6.6.
    access_token_cifrado: Mapped[bytes] = mapped_column(BYTEA)
    client_secret_cifrado: Mapped[bytes] = mapped_column(BYTEA)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
