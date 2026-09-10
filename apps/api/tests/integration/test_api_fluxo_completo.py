"""Teste de integração ponta a ponta via HTTP (ASGI in-process, sem servidor
real) — valida o wiring completo: routers, DI, schemas Pydantic, exception
handlers RFC 7807 e o dependency override de sessão de banco para o Postgres
de teste. Usa o usuário admin criado por `migrations/000002_seed_dev.up.sql`
(aplicado automaticamente pela fixture `test_engine`).

Nota: este teste não limpa os dados que cria (produto/variante/pedido) — como
não há nenhuma constraint de unicidade violável entre execuções (SKU é
gerado com sufixo aleatório), é seguro rodar repetidamente contra o mesmo
banco de teste local, apenas acumulando linhas irrelevantes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration


async def test_fluxo_completo_login_produto_variante_pedido(test_engine) -> None:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def _override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login_resp = await client.post(
                "/auth/login", json={"email": "admin@amactive.dev", "senha": "amactive123"}
            )
            assert login_resp.status_code == 200, login_resp.text
            token = login_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            produto_resp = await client.post(
                "/produtos", json={"nome": "Top Teste API", "marca": "AMACTIVE"}, headers=headers
            )
            assert produto_resp.status_code == 201, produto_resp.text
            produto_id = produto_resp.json()["id"]

            variante_resp = await client.post(
                f"/produtos/{produto_id}/variantes",
                json={"tamanho": "M", "cor": "Azul", "preco_venda": "79.90", "estoque_inicial": 5},
                headers=headers,
            )
            assert variante_resp.status_code == 201, variante_resp.text
            variante = variante_resp.json()
            assert variante["quantidade_estoque"] == 5

            pedido_resp = await client.post(
                "/pedidos",
                json={
                    "itens": [{"variante_id": variante["id"], "quantidade": 2}],
                    "pagamentos": [{"forma_pagamento": "PIX", "valor": "159.80"}],
                },
                headers=headers,
            )
            assert pedido_resp.status_code == 201, pedido_resp.text
            pedido = pedido_resp.json()
            assert pedido["status"] == "CONFIRMADO"
            assert pedido["valor_total"] == "159.80"
            assert pedido["itens"][0]["sku"] == variante["sku"]

            # Compra de mais 10 unidades do que existe em estoque -> 422 RFC 7807.
            pedido_invalido_resp = await client.post(
                "/pedidos",
                json={
                    "itens": [{"variante_id": variante["id"], "quantidade": 999}],
                    "pagamentos": [{"forma_pagamento": "PIX", "valor": "79820.10"}],
                },
                headers=headers,
            )
            assert pedido_invalido_resp.status_code == 422
            problema = pedido_invalido_resp.json()
            assert problema["type"] == "https://amactive.dev/errors/estoque-insuficiente"

            sem_token_resp = await client.get("/produtos")
            assert sem_token_resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
