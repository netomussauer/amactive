"""Vitrine via HTTP (ASGI in-process): rotas públicas, schemas, erros RFC 7807 e
o fluxo completo checkout -> confirmação pela equipe -> disponibilidade.

Usa a transação isolada do `db_session` (rollback no teardown), injetada como
sessão da aplicação via dependency override."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.infrastructure.persistence.models import ProdutoModel
from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration

NOME_PRODUTO = "Legging Fitness Teste"


@pytest.fixture
async def cliente_http(db_session: AsyncSession):
    async def _sessao_de_teste():
        yield db_session

    app.dependency_overrides[get_db_session] = _sessao_de_teste
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)


async def _token_admin(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/auth/login", json={"email": "admin@amactive.dev", "senha": "amactive123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_catalogo_publico_lista_e_detalha_sem_login(
    cliente_http: AsyncClient, db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=3, preco_venda="100.00")
    await db_session.execute(
        update(ProdutoModel)
        .where(ProdutoModel.nome == NOME_PRODUTO)
        .values(desconto_percentual=Decimal(10))
    )

    lista = await cliente_http.get("/loja/produtos", params={"q": NOME_PRODUTO})
    assert lista.status_code == 200, lista.text
    corpo = lista.json()
    assert corpo["pagination"]["total"] == 1
    produto = corpo["data"][0]
    assert produto["desconto_percentual"] == "10.00"
    assert produto["preco_a_partir_de"] == "90.00"  # com desconto aplicado

    detalhe = await cliente_http.get(f"/loja/produtos/{produto['id']}")
    assert detalhe.status_code == 200, detalhe.text
    (item,) = detalhe.json()["variantes"]
    assert item["id"] == str(variante.id)
    assert item["preco_cheio"] == "100.00"
    assert item["preco_unitario"] == "90.00"
    assert item["disponivel"] == 3
    # Campos internos nunca saem na vitrine.
    assert "preco_custo" not in item
    assert "estoque_minimo" not in item


async def test_produto_inexistente_responde_problem_details(cliente_http: AsyncClient) -> None:
    resp = await cliente_http.get(f"/loja/produtos/{uuid.uuid4()}")

    assert resp.status_code == 404
    assert resp.json()["type"].endswith("/nao-encontrado")


async def test_checkout_reserva_e_equipe_confirma_pagamento(
    cliente_http: AsyncClient, db_session: AsyncSession, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=3, preco_venda="100.00")
    payload = {
        "cliente": {"nome": "Ana Cliente", "telefone": "(11) 99999-0001"},
        "itens": [{"variante_id": str(variante.id), "quantidade": 2}],
    }

    criado = await cliente_http.post("/loja/pedidos", json=payload)
    assert criado.status_code == 201, criado.text
    pedido = criado.json()
    assert pedido["numero"].startswith("PED-")
    assert pedido["status"] == "PENDENTE"
    assert pedido["valor_total"] == "200.00"
    assert pedido["reservado_ate"]
    assert NOME_PRODUTO in pedido["itens"][0]["descricao"]

    # A vitrine já mostra só 1 disponível; um segundo checkout de 2 é recusado.
    segundo = await cliente_http.post("/loja/pedidos", json=payload)
    assert segundo.status_code == 422
    assert segundo.json()["type"].endswith("/estoque-insuficiente")

    # A equipe localiza o pedido na lista administrativa (autenticada) e confirma
    # o pagamento. O id interno não é exposto no checkout público, de propósito.
    headers = await _token_admin(cliente_http)
    fila = await cliente_http.get(
        "/pedidos", params={"origem_canal": "VITRINE", "status": "PENDENTE"}, headers=headers
    )
    assert fila.status_code == 200, fila.text
    pedido_admin = next(p for p in fila.json()["data"] if p["numero"] == pedido["numero"])
    confirmado = await cliente_http.post(
        f"/pedidos/{pedido_admin['id']}/confirmar-pagamento",
        json={"pagamentos": [{"forma_pagamento": "PIX", "valor": "200.00"}]},
        headers=headers,
    )
    assert confirmado.status_code == 200, confirmado.text
    assert confirmado.json()["status"] == "CONFIRMADO"
    # O pedido continua sem operador de criação; quem confirmou fica na
    # movimentação de estoque (auditoria), não no pedido.
    assert confirmado.json()["usuario_id"] is None
    assert confirmado.json()["origem_canal"] == "VITRINE"

    # Com a baixa real, o saldo público passa a ser 1 (3 - 2).
    lista = await cliente_http.get("/loja/produtos", params={"q": NOME_PRODUTO})
    produto_id = lista.json()["data"][0]["id"]
    detalhe = await cliente_http.get(f"/loja/produtos/{produto_id}")
    assert detalhe.json()["variantes"][0]["disponivel"] == 1


async def test_checkout_rejeita_telefone_invalido_e_campos_extras(
    cliente_http: AsyncClient, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=3)

    sem_ddd = await cliente_http.post(
        "/loja/pedidos",
        json={
            "cliente": {"nome": "Ana", "telefone": "123"},
            "itens": [{"variante_id": str(variante.id), "quantidade": 1}],
        },
    )
    assert sem_ddd.status_code == 422
    assert sem_ddd.json()["type"].endswith("/erro-validacao")


async def test_registro_manual_do_pdv_nao_aceita_origem_vitrine(
    cliente_http: AsyncClient, criar_variante_com_estoque
) -> None:
    variante = await criar_variante_com_estoque(quantidade_inicial=3)
    headers = await _token_admin(cliente_http)

    resp = await cliente_http.post(
        "/pedidos",
        json={
            "origem_canal": "VITRINE",
            "itens": [{"variante_id": str(variante.id), "quantidade": 1}],
            "pagamentos": [{"forma_pagamento": "PIX", "valor": "100.00"}],
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["type"].endswith("/erro-validacao")


async def test_confirmacao_exige_autenticacao(cliente_http: AsyncClient) -> None:
    resp = await cliente_http.post(
        f"/pedidos/{uuid.uuid4()}/confirmar-pagamento",
        json={"pagamentos": [{"forma_pagamento": "PIX", "valor": "1.00"}]},
    )
    assert resp.status_code == 401
