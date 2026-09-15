"""Testes unitários dos mappers puros payload Nuvemshop <-> DTOs internos
(design §7, avaliação §1.2/§1.3)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from amactive.contexts.integracao_canais.domain.repositories import (
    ProdutoParaPublicacao,
    VarianteParaPublicacao,
)
from amactive.contexts.integracao_canais.infrastructure.nuvemshop.mappers import (
    mapear_pedido_nuvemshop,
    mapear_resultado_publicacao,
    montar_payload_produto,
)

pytestmark = pytest.mark.unit


def _payload_pedido(**sobrescritas: object) -> dict:
    payload = {
        "id": 555000111,
        "customer": {
            "id": 999888,
            "name": "Ana Compradora",
            "email": "ana@example.com",
            "identification": "12345678900",
            "phone": "11999990000",
        },
        "shipping_address": {
            "address": "Rua das Flores, 10",
            "city": "São Paulo",
            "province": "SP",
            "zipcode": "01000-000",
        },
        "products": [
            {
                "product_id": 111,
                "variant_id": 222,
                "sku": "SKU-1",
                "quantity": "2",
                "price": "50.00",
            },
            {"product_id": 111, "variant_id": 223, "sku": "SKU-2", "quantity": 1, "price": "99.90"},
        ],
        "total": "199.90",
        "status": "open",
        "payment_status": "paid",
    }
    payload.update(sobrescritas)
    return payload


def test_mapear_pedido_traduz_cliente_endereco_e_itens() -> None:
    dto = mapear_pedido_nuvemshop(_payload_pedido())

    assert dto.pedido_externo_id == "555000111"
    assert dto.cliente_email == "ana@example.com"
    assert dto.cliente_nome == "Ana Compradora"
    assert dto.cliente_cpf_cnpj == "12345678900"
    assert dto.cliente_telefone == "11999990000"
    assert dto.cliente_externo_id == "999888"
    assert dto.cliente_endereco is not None
    assert dto.cliente_endereco.logradouro == "Rua das Flores, 10"
    assert dto.cliente_endereco.cidade == "São Paulo"
    assert dto.cliente_endereco.uf == "SP"
    assert dto.cliente_endereco.cep == "01000-000"
    assert dto.valor_total == Decimal("199.90")
    assert len(dto.itens) == 2
    assert dto.itens[0].produto_externo_id == "111"
    assert dto.itens[0].variante_externo_id == "222"
    assert dto.itens[0].quantidade == 2
    assert dto.itens[1].quantidade == 1


def test_mapear_pedido_usa_campos_contact_quando_nao_ha_customer() -> None:
    payload = _payload_pedido(
        customer=None,
        contact_email="convidado@example.com",
        contact_name="Convidado",
        contact_identification=None,
        contact_phone=None,
    )

    dto = mapear_pedido_nuvemshop(payload)

    assert dto.cliente_email == "convidado@example.com"
    assert dto.cliente_nome == "Convidado"
    # Sem customer.id nem contact_*, cai no fallback do id do pedido.
    assert dto.cliente_externo_id == "555000111"


def test_mapear_pedido_sem_endereco_de_entrega_retorna_none() -> None:
    dto = mapear_pedido_nuvemshop(_payload_pedido(shipping_address=None))

    assert dto.cliente_endereco is None


def _produto_para_publicacao() -> ProdutoParaPublicacao:
    variante_1 = VarianteParaPublicacao(
        variante_id=uuid4(), sku="SKU-1", tamanho="M", cor="Preto", preco_venda=Decimal("99.90")
    )
    variante_2 = VarianteParaPublicacao(
        variante_id=uuid4(), sku="SKU-2", tamanho="G", cor="Preto", preco_venda=Decimal("99.90")
    )
    return ProdutoParaPublicacao(
        produto_id=uuid4(),
        nome="Legging Fitness",
        descricao="Legging de alta compressão",
        variantes=[variante_1, variante_2],
    )


def test_montar_payload_produto_inclui_nome_descricao_e_variantes() -> None:
    produto = _produto_para_publicacao()

    payload = montar_payload_produto(produto)

    assert payload["name"] == {"pt": "Legging Fitness"}
    assert payload["description"] == {"pt": "Legging de alta compressão"}
    assert len(payload["variants"]) == 2
    assert payload["variants"][0]["sku"] == "SKU-1"
    assert payload["variants"][0]["price"] == "99.90"
    assert payload["variants"][0]["values"] == [{"pt": "Preto"}, {"pt": "M"}]


def test_mapear_resultado_publicacao_casa_variantes_por_sku() -> None:
    produto = _produto_para_publicacao()
    variante_1_id, variante_2_id = (v.variante_id for v in produto.variantes)
    payload_resposta = {
        "id": 42,
        "variants": [
            # Ordem invertida em relação ao envio — casamento é por SKU, não
            # por posição.
            {"id": 902, "sku": "SKU-2"},
            {"id": 901, "sku": "SKU-1"},
        ],
    }

    resultado = mapear_resultado_publicacao(payload_resposta, produto)

    assert resultado.produto_externo_id == "42"
    assert resultado.variantes_externo_id[str(variante_1_id)] == "901"
    assert resultado.variantes_externo_id[str(variante_2_id)] == "902"


def test_mapear_resultado_publicacao_ignora_variante_de_sku_desconhecido() -> None:
    produto = _produto_para_publicacao()
    payload_resposta = {
        "id": 42,
        "variants": [{"id": 999, "sku": "SKU-NUNCA-ENVIADO"}],
    }

    resultado = mapear_resultado_publicacao(payload_resposta, produto)

    assert resultado.variantes_externo_id == {}
