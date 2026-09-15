"""Tipos ENUM nativos do PostgreSQL, espelhando `migrations/000001_initial_schema.up.sql`.

Centralizados aqui (em vez de redeclarados em cada `infrastructure/persistence/models.py`)
para que todos os contextos referenciem exatamente os mesmos nomes/valores de tipo.
`create_type=False` é obrigatório: os tipos já existem fisicamente, criados pela
migration SQL pura (ver ADR-003 em docs/SDD.md) — o SQLAlchemy nunca deve tentar
criá-los ou alterá-los.
"""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import ENUM as PGEnum

papel_usuario_enum = PGEnum(
    "ADMIN", "VENDEDOR", "ESTOQUISTA", name="papel_usuario", create_type=False
)

tipo_movimentacao_enum = PGEnum(
    "ENTRADA", "SAIDA", "AJUSTE", name="tipo_movimentacao", create_type=False
)

motivo_movimentacao_enum = PGEnum(
    "COMPRA",
    "VENDA",
    "AJUSTE_INVENTARIO",
    "DEVOLUCAO",
    "PERDA",
    name="motivo_movimentacao",
    create_type=False,
)

status_pedido_enum = PGEnum(
    "PENDENTE", "CONFIRMADO", "CANCELADO", name="status_pedido", create_type=False
)

forma_pagamento_enum = PGEnum(
    "DINHEIRO",
    "PIX",
    "CARTAO_DEBITO",
    "CARTAO_CREDITO",
    # Valor aditivo (migrations/000005_integracao_nuvemshop) — "pago
    # externamente via checkout do canal", ver docs/design-integracao-
    # nuvemshop.md §3.1.
    "NUVEMSHOP",
    name="forma_pagamento",
    create_type=False,
)

origem_canal_pedido_enum = PGEnum("PDV", "NUVEMSHOP", name="origem_canal_pedido", create_type=False)

origem_cadastro_cliente_enum = PGEnum(
    "MANUAL", "NUVEMSHOP", name="origem_cadastro_cliente", create_type=False
)

# ─────────────────────────────────────────────────────────────
# Vocabulário do bounded context `integracao_canais`
# (migrations/000005_integracao_nuvemshop), ver docs/design-integracao-
# nuvemshop.md §2.3/§6.1. `canal_integracao` é um tipo Postgres diferente de
# `origem_canal_pedido`/`origem_cadastro_cliente` acima — cada contexto
# nomeia/versiona seu próprio enum mesmo compartilhando o valor literal
# "NUVEMSHOP" hoje.
# ─────────────────────────────────────────────────────────────
canal_integracao_enum = PGEnum("NUVEMSHOP", name="canal_integracao", create_type=False)

status_webhook_evento_enum = PGEnum(
    "PENDENTE",
    "PROCESSADO",
    "ERRO",
    "CONFLITO_MANUAL",
    name="status_webhook_evento",
    create_type=False,
)

status_outbox_enum = PGEnum("PENDENTE", "ENVIADO", "ERRO", name="status_outbox", create_type=False)

operacao_catalogo_outbox_enum = PGEnum(
    "CRIAR", "ATUALIZAR", name="operacao_catalogo_outbox", create_type=False
)
