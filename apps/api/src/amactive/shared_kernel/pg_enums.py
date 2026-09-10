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
    name="forma_pagamento",
    create_type=False,
)
