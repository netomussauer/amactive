"""Portas (Protocols) do contexto Integração de Canais — ver
docs/design-integracao-nuvemshop.md §2.5.

Os DTOs somente-leitura que fazem parte da assinatura de uma porta
(`NuvemshopPedidoDTO`, `ProdutoParaPublicacao`, `PublicacaoResultado`,
`EnderecoExterno`, `CredencialDecifrada`, ...) são definidos aqui mesmo,
junto da porta — mesmo padrão já usado por `vendas/domain/repositories.py`
(`VarianteVenda`): DTOs de porta vivem no domínio, não na camada de
aplicação, para não inverter a direção de dependência (aplicação depende do
domínio, nunca o contrário). `application/dto.py` reexporta estes tipos para
uso conveniente pelos casos de uso, seguindo a estrutura de pastas do design
§2.2. Os campos exatos destes DTOs são um primeiro recorte suficiente para
tipar as portas deste esqueleto — podem ser refinados pelos passos que de
fato os populam/consomem (`client.py`/`mappers.py` no passo 5,
`catalogo_gateway.py` no passo 6, ver design §9).

Implementação concreta de todos os Protocols abaixo vive em
`infrastructure/` (passos 5 e 6 desta sequência) — nada aqui tem lógica de
negócio.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from amactive.contexts.integracao_canais.domain.entities import (
    CanalIntegracao,
    IntegracaoCatalogoOutbox,
    IntegracaoEstoqueOutbox,
    MapeamentoVarianteCanal,
    WebhookEvento,
)
from amactive.contexts.vendas.application.dto import ItemPedidoInput, PagamentoInput
from amactive.contexts.vendas.domain.entities import OrigemCanalPedido, Pedido


# ─────────────────────────────────────────────────────────────
# DTOs de porta — ACL entre o vocabulário Nuvemshop e o domínio interno
# ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class ItemPedidoExternoDTO:
    """Um item do pedido externo, já traduzido do payload cru da Nuvemshop
    (referenciando IDs externos — a resolução para `variante_id` AMACTIVE é
    feita via `MapeamentoVarianteRepository`, não aqui)."""

    variante_externo_id: str
    produto_externo_id: str
    quantidade: int


@dataclass(frozen=True)
class EnderecoExterno:
    """Endereço do comprador vindo do payload do pedido externo (design
    §3.3) — mapeado para os campos `endereco_*` de `Cliente` via
    `ClienteIntegracaoPort`."""

    logradouro: str | None
    cidade: str | None
    uf: str | None
    cep: str | None


@dataclass(frozen=True)
class NuvemshopPedidoDTO:
    """Pedido já traduzido, obtido via `NuvemshopClientPort.buscar_pedido`
    (`GET /orders/{id}`, design §5.3 passo 1) — o payload do webhook não
    traz o recurso completo, esta chamada é obrigatória."""

    pedido_externo_id: str
    cliente_email: str
    cliente_nome: str
    cliente_cpf_cnpj: str | None
    cliente_telefone: str | None
    cliente_endereco: EnderecoExterno | None
    cliente_externo_id: str
    itens: list[ItemPedidoExternoDTO]
    valor_total: Decimal


@dataclass(frozen=True)
class VarianteParaPublicacao:
    """Uma variante dentro de `ProdutoParaPublicacao` — sku/tamanho/cor/preço
    já calculados (design §3.2)."""

    variante_id: UUID
    sku: str
    tamanho: str
    cor: str
    preco_venda: Decimal


@dataclass(frozen=True)
class ImagemParaPublicacao:
    """Uma imagem da galeria de um produto, por cor (design §3.2/§4) —
    montada a partir de `ImagemRepository.listar_por_produto` (contexto
    Catálogo & Estoque), lida por `catalogo_gateway.py`, nunca escrita por
    `integracao_canais`."""

    cor: str
    url: str
    ordem: int
    principal: bool


@dataclass(frozen=True)
class ProdutoParaPublicacao:
    """Produto pronto para publicação na Nuvemshop, montado por
    `CatalogoIntegracaoPort.buscar_produto_para_publicacao` (somente
    leitura, design §3.2) — nome/descrição/variantes/galeria de imagens por
    cor.

    `imagens` tem default (`[]`) para preservar retrocompatibilidade com
    testes/código já escritos contra o recorte inicial deste DTO (passos
    5/6, ver docs/design-integracao-nuvemshop.md §9) — nenhuma linha
    existente que constrói `ProdutoParaPublicacao` sem esse campo precisa
    mudar."""

    produto_id: UUID
    nome: str
    descricao: str | None
    variantes: list[VarianteParaPublicacao]
    imagens: list[ImagemParaPublicacao] = field(default_factory=list)


@dataclass(frozen=True)
class PublicacaoResultado:
    """Resultado de `criar_produto`/`atualizar_produto` no
    `NuvemshopClientPort` — IDs externos atribuídos pela Nuvemshop, usados
    para popular/atualizar `MapeamentoVarianteCanal`."""

    produto_externo_id: str
    variantes_externo_id: dict[str, str]


@dataclass(frozen=True)
class CredencialDecifrada:
    """Retorno de `CredencialCanalRepository.buscar_token_decifrado` — token
    e secret já decifrados (`pgp_sym_decrypt`), nunca persistidos fora do
    processo do worker além do necessário (design §7.2)."""

    canal: CanalIntegracao
    store_id: str
    access_token: str
    client_secret: str


# ─────────────────────────────────────────────────────────────
# Portas publicadas por `integracao_canais` para seus próprios casos de uso
# ─────────────────────────────────────────────────────────────
class NuvemshopClientPort(Protocol):
    """ACL do cliente HTTP da Nuvemshop — ver design §7. Implementação
    concreta (rate limiter, retry, autenticação) é
    `infrastructure/nuvemshop/client.py`, passo 5 desta sequência."""

    async def buscar_pedido(self, pedido_externo_id: str) -> NuvemshopPedidoDTO: ...

    async def criar_produto(self, produto: ProdutoParaPublicacao) -> PublicacaoResultado: ...

    async def atualizar_produto(
        self, produto_externo_id: str, produto: ProdutoParaPublicacao
    ) -> PublicacaoResultado: ...

    async def atualizar_estoque_variante(
        self, *, produto_externo_id: str, variante_externo_id: str, quantidade: int
    ) -> None:
        """`produto_externo_id` é exigido porque o endpoint real da
        Nuvemshop precisa dele no path (`PUT /products/{id}/variants/{id}`,
        avaliação §1.2) — o chamador (worker do outbox de estoque, passo 7)
        sempre tem essa informação disponível via `MapeamentoVarianteCanal`
        antes de chegar aqui, então não há razão para o client resolvê-lo
        internamente."""
        ...


class WebhookVerifierPort(Protocol):
    """HMAC-SHA256 do corpo bruto do webhook — ver design §5.1.
    Implementação em `infrastructure/nuvemshop/webhook_verifier.py`, passo
    5."""

    def verificar(self, *, corpo_bruto: bytes, assinatura: str, client_secret: str) -> bool: ...


class WebhookEventoRepository(Protocol):
    async def registrar_se_novo(
        self,
        *,
        canal: CanalIntegracao,
        tipo_evento: str,
        id_recurso_externo: str,
        payload_bruto: dict,
    ) -> WebhookEvento | None:
        """INSERT ... ON CONFLICT (evento_externo_id) DO NOTHING — retorna
        None se duplicado."""
        ...

    async def buscar_lote_pendente(self, *, limite: int) -> list[WebhookEvento]:
        """SELECT ... FOR UPDATE SKIP LOCKED, status IN ('PENDENTE', 'ERRO')."""
        ...

    async def marcar_processado(self, evento_id: UUID) -> None: ...

    async def marcar_erro(self, evento_id: UUID, *, detalhe: str) -> None: ...

    async def marcar_conflito_manual(self, evento_id: UUID, *, detalhe: str) -> None: ...


class MapeamentoVarianteRepository(Protocol):
    async def buscar_por_variante_externo(
        self, *, canal: CanalIntegracao, variante_externo_id: str
    ) -> MapeamentoVarianteCanal | None: ...

    async def buscar_por_variante_id(
        self, *, variante_id: UUID, canal: CanalIntegracao
    ) -> MapeamentoVarianteCanal | None: ...

    async def upsert(
        self,
        *,
        variante_id: UUID,
        canal: CanalIntegracao,
        produto_externo_id: str,
        variante_externo_id: str,
    ) -> MapeamentoVarianteCanal: ...


class IntegracaoEstoqueOutboxRepository(Protocol):
    async def buscar_lote_pendente_coalescido(
        self, *, limite: int
    ) -> list[IntegracaoEstoqueOutbox]:
        """DISTINCT ON (variante_id) ... ORDER BY variante_id, criado_em DESC
        — ver design §4.2."""
        ...

    async def marcar_enviado(self, outbox_id: UUID, *, superseded_ids: list[UUID]) -> None: ...

    async def marcar_erro_com_retry(
        self, outbox_id: UUID, *, detalhe: str, proxima_tentativa_em: datetime
    ) -> None: ...

    async def contar_pendentes(self) -> int:
        """`SELECT count(*) ... WHERE status IN ('PENDENTE', 'ERRO')` — usada
        por `run_worker.py` para atualizar o gauge
        `integracao_outbox_pendente{fila="estoque"}` (design §8), sem
        nenhuma query nova além da já necessária para o alerta operacional."""
        ...


class IntegracaoCatalogoOutboxRepository(Protocol):
    """Mesma forma de `IntegracaoEstoqueOutboxRepository`, chave
    `produto_id` (design §4.2)."""

    async def buscar_lote_pendente_coalescido(
        self, *, limite: int
    ) -> list[IntegracaoCatalogoOutbox]: ...

    async def marcar_enviado(self, outbox_id: UUID, *, superseded_ids: list[UUID]) -> None: ...

    async def marcar_erro_com_retry(
        self, outbox_id: UUID, *, detalhe: str, proxima_tentativa_em: datetime
    ) -> None: ...

    async def contar_pendentes(self) -> int:
        """Idem `IntegracaoEstoqueOutboxRepository.contar_pendentes`, para o
        gauge `integracao_outbox_pendente{fila="catalogo"}`."""
        ...


class CredencialCanalRepository(Protocol):
    async def buscar_token_decifrado(
        self, canal: CanalIntegracao
    ) -> CredencialDecifrada | None: ...


# ─────────────────────────────────────────────────────────────
# Portas consumidas de outros contextos (design §3) — Shared Kernel
# restrito, mesmo padrão de `CatalogoPort`/`EstoquePort` em
# `vendas/domain/repositories.py`. A implementação concreta vive nos
# gateways de `infrastructure/gateways/` (passo 6).
# ─────────────────────────────────────────────────────────────
class PedidoIntegracaoPort(Protocol):
    """Implementado por `infrastructure/gateways/vendas_gateway.py`,
    chamando `CriarPedidoUseCase` in-process (design §3.1/§3.4) — nunca
    acessa `pedido`/`item_pedido` diretamente."""

    async def confirmar_pedido_externo(
        self,
        *,
        cliente_id: UUID,
        itens: list[ItemPedidoInput],
        pagamentos: list[PagamentoInput],
        origem_canal: OrigemCanalPedido,
        pedido_externo_id: str,
    ) -> Pedido: ...


class ClienteIntegracaoPort(Protocol):
    """Implementado por `infrastructure/gateways/cadastros_gateway.py`,
    chamando `ClienteRepository.upsert_por_email` (design §3.3)."""

    async def resolver_ou_criar_por_email(
        self,
        *,
        email: str,
        nome: str,
        cpf_cnpj: str | None,
        telefone: str | None,
        endereco: EnderecoExterno | None,
        cliente_externo_id: str,
    ) -> UUID: ...


class CatalogoIntegracaoPort(Protocol):
    """Implementado por `infrastructure/gateways/catalogo_gateway.py`,
    somente leitura (design §3.2) — nunca chama
    `ProdutoRepository.criar/atualizar` nem `MovimentacaoRepository.registrar`."""

    async def buscar_produto_para_publicacao(self, produto_id: UUID) -> ProdutoParaPublicacao: ...

    async def buscar_saldo_estoque(self, variante_id: UUID) -> int: ...
