"""Tradução entre o payload cru da API da Nuvemshop e os DTOs internos do
contexto (`domain/repositories.py`) — ver docs/design-integracao-nuvemshop.md
§7 e docs/avaliacao-integracao-nuvemshop.md §1.2/§1.3/§1.4.

Todas as funções aqui são puras (sem I/O, sem `httpx`) — `client.py` é o
único módulo que efetivamente chama a rede e usa estes mappers para
traduzir request/response.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from amactive.contexts.integracao_canais.domain.repositories import (
    EnderecoExterno,
    ItemPedidoExternoDTO,
    NuvemshopPedidoDTO,
    ProdutoParaPublicacao,
    PublicacaoResultado,
    VarianteParaPublicacao,
)

# Formato multi-idioma (`{"pt": "..."}`) é o aceito pela API da Nuvemshop
# para `name`/`description`/`attributes`/`values` de produto (avaliação
# §1.2), independentemente de a loja ter um ou vários idiomas configurados
# — usar sempre o dict evita o client precisar saber quantos idiomas a loja
# tem configurados.
_LOCALE_PADRAO = "pt"


def mapear_pedido_nuvemshop(payload: dict[str, Any]) -> NuvemshopPedidoDTO:
    """Traduz o payload cru de `GET /orders/{id}` (avaliação §1.3) para
    `NuvemshopPedidoDTO` — a webhook não traz o pedido completo, esta
    chamada é sempre necessária (design §5.3).

    Dados do comprador são lidos preferencialmente do objeto `customer`
    (id/name/email/identification/phone); os campos `contact_*` no nível
    raiz do pedido são o fallback documentado para pedidos sem cadastro de
    cliente vinculado (checkout de convidado)."""
    customer = payload.get("customer") or {}
    cliente_email = customer.get("email") or payload.get("contact_email") or ""
    cliente_nome = customer.get("name") or payload.get("contact_name") or ""
    cliente_cpf_cnpj = customer.get("identification") or payload.get("contact_identification")
    cliente_telefone = customer.get("phone") or payload.get("contact_phone")
    # Fallback para o id do próprio pedido é defensivo (não deveria
    # acontecer na prática — todo pedido da Nuvemshop tem um customer
    # associado), mas garante que `cliente_externo_id` (campo obrigatório do
    # DTO) nunca fique vazio.
    cliente_externo_id = str(customer.get("id") or payload["id"])

    return NuvemshopPedidoDTO(
        pedido_externo_id=str(payload["id"]),
        cliente_email=cliente_email,
        cliente_nome=cliente_nome,
        cliente_cpf_cnpj=cliente_cpf_cnpj,
        cliente_telefone=cliente_telefone,
        cliente_endereco=_mapear_endereco(payload.get("shipping_address")),
        cliente_externo_id=cliente_externo_id,
        itens=[_mapear_item(item) for item in payload.get("products", [])],
        valor_total=Decimal(str(payload["total"])),
    )


def _mapear_endereco(bruto: dict[str, Any] | None) -> EnderecoExterno | None:
    if not bruto:
        return None
    return EnderecoExterno(
        logradouro=bruto.get("address"),
        cidade=bruto.get("city"),
        uf=bruto.get("province"),
        cep=bruto.get("zipcode"),
    )


def _mapear_item(bruto: dict[str, Any]) -> ItemPedidoExternoDTO:
    return ItemPedidoExternoDTO(
        variante_externo_id=str(bruto["variant_id"]),
        produto_externo_id=str(bruto["product_id"]),
        # `quantity` pode chegar como string na API real — normaliza via
        # Decimal antes de truncar para int (evita `ValueError` de
        # `int("2.0")`, ainda que a Nuvemshop não deva mandar fracionário
        # para uma unidade vendável inteira).
        quantidade=int(Decimal(str(bruto["quantity"]))),
    )


def montar_payload_produto(produto: ProdutoParaPublicacao) -> dict[str, Any]:
    """Monta o payload de `POST`/`PUT /products` (design §3.3, avaliação
    §1.2) a partir de `ProdutoParaPublicacao`. Granularidade é sempre o
    produto inteiro (todas as variantes), nunca uma variante isolada —
    mesma decisão do outbox de catálogo (design §2.4/§4)."""
    return {
        "name": {_LOCALE_PADRAO: produto.nome},
        "description": {_LOCALE_PADRAO: produto.descricao or ""},
        # Duas dimensões fixas (cor, tamanho) — reflete o modelo de
        # `produto_variante` do AMACTIVE (avaliação §3.4: colunas fixas, não
        # atributos genéricos), traduzido para o vocabulário de atributos
        # multi-dimensional da Nuvemshop.
        "attributes": [{_LOCALE_PADRAO: "Cor"}, {_LOCALE_PADRAO: "Tamanho"}],
        "variants": [_montar_payload_variante(variante) for variante in produto.variantes],
    }


def _montar_payload_variante(variante: VarianteParaPublicacao) -> dict[str, Any]:
    return {
        "sku": variante.sku,
        # A API espera preço como string decimal (avaliação §1.2) — nunca
        # float, para não introduzir erro de arredondamento binário.
        "price": str(variante.preco_venda),
        "stock_management": True,
        "values": [{_LOCALE_PADRAO: variante.cor}, {_LOCALE_PADRAO: variante.tamanho}],
    }


def mapear_resultado_publicacao(
    payload_resposta: dict[str, Any], produto: ProdutoParaPublicacao
) -> PublicacaoResultado:
    """Traduz a resposta de `POST`/`PUT /products` para `PublicacaoResultado`
    — usada por `MapeamentoVarianteRepository.upsert` (passo 6/7) para
    gravar `produto_externo_id`/`variante_externo_id` por variante AMACTIVE.

    O casamento entre a variante submetida e a variante devolvida pela
    Nuvemshop é feito por `sku` (não pela ordem da lista) — o SKU que
    enviamos é o mesmo que a API devolve no mesmo produto, e usar SKU em vez
    de posição é robusto mesmo que a Nuvemshop reordene as variantes na
    resposta. Uma variante devolvida cujo SKU não bate com nenhuma enviada é
    ignorada (defensivo: não deveria acontecer, mas não deve corromper o
    mapeamento de outra variante caso aconteça)."""
    sku_para_variante_id = {
        variante.sku: str(variante.variante_id) for variante in produto.variantes
    }
    variantes_externo_id: dict[str, str] = {}
    for variante_resposta in payload_resposta.get("variants", []):
        variante_id_amactive = sku_para_variante_id.get(variante_resposta.get("sku"))
        if variante_id_amactive is None:
            continue
        variantes_externo_id[variante_id_amactive] = str(variante_resposta["id"])

    return PublicacaoResultado(
        produto_externo_id=str(payload_resposta["id"]),
        variantes_externo_id=variantes_externo_id,
    )
