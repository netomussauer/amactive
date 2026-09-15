"""Entidades do contexto Integração de Canais — ver
docs/design-integracao-nuvemshop.md §2.3/§2.4.

Anti-Corruption Layer isolada (Supporting Subdomain, ver design §2.1): o
vocabulário externo (rate limit, HMAC, ``location_id``, IDs da Nuvemshop)
nunca vaza para os contextos Core (`vendas`, `catalogo_estoque`,
`cadastros`). Todas as entidades seguem o padrão já usado em
`vendas/domain/entities.py`: ``@dataclass(frozen=True)``, sem métodos de
persistência, sem import de infraestrutura.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from uuid import UUID


class CanalIntegracao(str, Enum):
    """Vocabulário de `integracao_canais` — identifica qual
    adaptador/credencial/mapeamento tratou o evento. Tipo Postgres
    **diferente** de `origem_canal_pedido` (vendas) e
    `origem_cadastro_cliente` (cadastros), que são vocabulário daqueles
    contextos mesmo compartilhando o valor literal "NUVEMSHOP" hoje — ver
    Nota de Ubiquitous Language, design §2.3."""

    NUVEMSHOP = "NUVEMSHOP"


class StatusWebhookEvento(str, Enum):
    PENDENTE = "PENDENTE"
    PROCESSADO = "PROCESSADO"
    ERRO = "ERRO"
    CONFLITO_MANUAL = "CONFLITO_MANUAL"


class StatusOutbox(str, Enum):
    PENDENTE = "PENDENTE"
    ENVIADO = "ENVIADO"
    ERRO = "ERRO"


class OperacaoCatalogoOutbox(str, Enum):
    CRIAR = "CRIAR"
    ATUALIZAR = "ATUALIZAR"


@dataclass(frozen=True)
class WebhookEvento:
    """Fila durável que desacopla a resposta HTTP (<3s) da lógica de
    negócio, e registro de auditoria de tudo que a Nuvemshop já tentou
    entregar, processado ou não (design §2.4).

    Invariante: `evento_externo_id` é construído como
    ``f"{canal.value}:{tipo_evento}:{id_recurso_externo}"`` — nunca o `id`
    bruto do payload sozinho, para que eventos diferentes sobre o mesmo
    recurso não colidam na constraint `UNIQUE`.
    """

    id: UUID
    canal: CanalIntegracao
    evento_externo_id: str
    tipo_evento: str
    id_recurso_externo: str
    payload_bruto: dict
    status: StatusWebhookEvento
    tentativas: int
    erro_detalhe: str | None
    recebido_em: datetime
    processado_em: datetime | None


@dataclass(frozen=True)
class MapeamentoVarianteCanal:
    """Fonte da verdade da correspondência `produto_variante` (AMACTIVE) <->
    `product_id`+`variant_id` (Nuvemshop) — nunca por SKU cru, que não é
    garantidamente único na Nuvemshop (design §2.4).

    Invariantes: `UNIQUE(variante_id, canal)` e
    `UNIQUE(canal, variante_externo_id)` — ver migration 000005.
    """

    id: UUID
    variante_id: UUID
    canal: CanalIntegracao
    produto_externo_id: str
    variante_externo_id: str
    criado_em: datetime
    atualizado_em: datetime | None


@dataclass(frozen=True)
class IntegracaoEstoqueOutbox:
    """Desacopla a escrita de estoque (rápida, transacional) do push HTTP
    lento e sujeito a rate limit para a Nuvemshop (design §2.4/§4).
    Populada por trigger de banco (`fn_enfileirar_outbox_estoque`), nunca
    por evento de domínio in-process — ver design §4.1.
    """

    id: UUID
    variante_id: UUID
    quantidade_publicada: int
    status: StatusOutbox
    tentativas: int
    proxima_tentativa_em: datetime | None
    erro_detalhe: str | None
    criado_em: datetime
    processado_em: datetime | None


@dataclass(frozen=True)
class IntegracaoCatalogoOutbox:
    """Mesma razão de `IntegracaoEstoqueOutbox`, para produto/variante/
    preço/imagem. Granularidade é o produto inteiro, não a variante (design
    §2.4). Populada por trigger de banco, ver design §4.1.
    """

    id: UUID
    produto_id: UUID
    operacao: OperacaoCatalogoOutbox
    status: StatusOutbox
    tentativas: int
    proxima_tentativa_em: datetime | None
    erro_detalhe: str | None
    criado_em: datetime
    processado_em: datetime | None


@dataclass(frozen=True)
class CredencialCanal:
    """Token permanente de app privado, altíssimo privilégio — nunca em
    texto puro em repouso (`pgp_sym_encrypt`, ver design §6.6/§7.2).
    `UNIQUE(canal)` na Fase 1 (uma única loja por canal).
    """

    id: UUID
    canal: CanalIntegracao
    store_id: str
    access_token_cifrado: bytes
    client_secret_cifrado: bytes
    criado_em: datetime
    atualizado_em: datetime | None
