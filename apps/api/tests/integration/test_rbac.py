"""Testes de integração de autorização por papel (RBAC) — ver
`core/security.requer_papel` e a matriz de permissões documentada em
`docs/openapi.yaml` (`x-roles` por operação). Cobre casos representativos de
cada bucket de regra da matriz (leitura aberta a todos vs. escrita
restrita, e os quatro recursos com regras assimétricas entre VENDEDOR e
ESTOQUISTA) — não as 9 linhas x 3 papéis exaustivamente, como orientado no
escopo do pedido de implementação.

Os tokens de VENDEDOR/ESTOQUISTA são emitidos diretamente via
`criar_access_token` (o fluxo de `/auth/login` em si já é coberto por
`test_api_fluxo_completo.py`); o usuário correspondente ainda precisa existir
na tabela `usuario` para satisfazer a FK de `pedido.usuario_id` /
`movimentacao_estoque.usuario_id` nos casos de sucesso de escrita."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from amactive.contexts.identidade.infrastructure.persistence.models import UsuarioModel
from amactive.core.security import criar_access_token
from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration


async def _criar_usuario(session: AsyncSession, *, papel: str) -> UsuarioModel:
    usuario = UsuarioModel(
        id=uuid.uuid4(),
        nome=f"Usuário RBAC {papel}",
        email=f"rbac-{papel.lower()}-{uuid.uuid4().hex[:8]}@amactive.dev",
        senha_hash="hash-nao-usado-neste-teste",
        papel=papel,
        ativo=True,
        criado_em=datetime.now(UTC),
    )
    session.add(usuario)
    await session.commit()
    return usuario


def _headers(usuario: UsuarioModel) -> dict[str, str]:
    token = criar_access_token(
        usuario_id=usuario.id, nome=usuario.nome, email=usuario.email, papel=usuario.papel
    )
    return {"Authorization": f"Bearer {token}"}


async def _headers_admin(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/auth/login", json={"email": "admin@amactive.dev", "senha": "amactive123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _criar_produto_com_variante(
    client: AsyncClient, admin_headers: dict[str, str], *, nome: str, estoque_inicial: int = 0
) -> dict[str, str]:
    produto_resp = await client.post(
        "/produtos", json={"nome": nome, "marca": "AMACTIVE"}, headers=admin_headers
    )
    assert produto_resp.status_code == 201, produto_resp.text
    produto_id = produto_resp.json()["id"]

    variante_resp = await client.post(
        f"/produtos/{produto_id}/variantes",
        json={
            "tamanho": "M",
            "cor": "Preto",
            "preco_venda": "59.90",
            "estoque_inicial": estoque_inicial,
        },
        headers=admin_headers,
    )
    assert variante_resp.status_code == 201, variante_resp.text
    return variante_resp.json()


@pytest_asyncio.fixture
async def rbac_client(
    test_engine: AsyncEngine,
) -> AsyncGenerator[tuple[AsyncClient, UsuarioModel, UsuarioModel], None]:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        async with session_factory() as setup_session:
            vendedor = await _criar_usuario(setup_session, papel="VENDEDOR")
            estoquista = await _criar_usuario(setup_session, papel="ESTOQUISTA")

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client, vendedor, estoquista
    finally:
        app.dependency_overrides.clear()


# ── Catálogo & Estoque: leitura aberta a todos, escrita ADMIN/ESTOQUISTA ──
async def test_vendedor_nao_pode_criar_produto(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, vendedor, _estoquista = rbac_client
    resp = await client.post(
        "/produtos",
        json={"nome": "Produto RBAC Vendedor", "marca": "AMACTIVE"},
        headers=_headers(vendedor),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["type"] == "https://amactive.dev/errors/acesso-negado"


async def test_estoquista_pode_criar_produto(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, _vendedor, estoquista = rbac_client
    resp = await client.post(
        "/produtos",
        json={"nome": "Produto RBAC Estoquista", "marca": "AMACTIVE"},
        headers=_headers(estoquista),
    )
    assert resp.status_code == 201, resp.text


async def test_vendedor_pode_listar_produtos(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, vendedor, _estoquista = rbac_client
    resp = await client.get("/produtos", headers=_headers(vendedor))
    assert resp.status_code == 200, resp.text


# ── Estoque: leitura aberta a todos, escrita ADMIN/ESTOQUISTA ──
async def test_estoquista_pode_registrar_movimentacao_estoque(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, _vendedor, estoquista = rbac_client
    admin_headers = await _headers_admin(client)
    variante = await _criar_produto_com_variante(
        client, admin_headers, nome="Produto RBAC Movimentação Estoquista"
    )

    resp = await client.post(
        "/estoque/movimentacoes",
        json={
            "variante_id": variante["id"],
            "tipo": "ENTRADA",
            "quantidade": 10,
            "motivo": "COMPRA",
        },
        headers=_headers(estoquista),
    )
    assert resp.status_code == 201, resp.text


async def test_vendedor_nao_pode_registrar_movimentacao_estoque(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, vendedor, _estoquista = rbac_client
    admin_headers = await _headers_admin(client)
    variante = await _criar_produto_com_variante(
        client, admin_headers, nome="Produto RBAC Movimentação Vendedor"
    )

    resp = await client.post(
        "/estoque/movimentacoes",
        json={
            "variante_id": variante["id"],
            "tipo": "ENTRADA",
            "quantidade": 5,
            "motivo": "COMPRA",
        },
        headers=_headers(vendedor),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["type"] == "https://amactive.dev/errors/acesso-negado"


# ── Pedidos: leitura aberta a todos, escrita ADMIN/VENDEDOR ──
async def test_vendedor_pode_criar_pedido(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, vendedor, _estoquista = rbac_client
    admin_headers = await _headers_admin(client)
    variante = await _criar_produto_com_variante(
        client, admin_headers, nome="Produto RBAC Pedido Vendedor", estoque_inicial=3
    )

    resp = await client.post(
        "/pedidos",
        json={
            "itens": [{"variante_id": variante["id"], "quantidade": 1}],
            "pagamentos": [{"forma_pagamento": "PIX", "valor": "59.90"}],
        },
        headers=_headers(vendedor),
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "CONFIRMADO"


async def test_estoquista_nao_pode_criar_pedido(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, _vendedor, estoquista = rbac_client
    admin_headers = await _headers_admin(client)
    variante = await _criar_produto_com_variante(
        client, admin_headers, nome="Produto RBAC Pedido Estoquista", estoque_inicial=3
    )

    resp = await client.post(
        "/pedidos",
        json={
            "itens": [{"variante_id": variante["id"], "quantidade": 1}],
            "pagamentos": [{"forma_pagamento": "PIX", "valor": "59.90"}],
        },
        headers=_headers(estoquista),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["type"] == "https://amactive.dev/errors/acesso-negado"


async def test_estoquista_pode_listar_pedidos(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, _vendedor, estoquista = rbac_client
    resp = await client.get("/pedidos", headers=_headers(estoquista))
    assert resp.status_code == 200, resp.text


# ── Clientes: ADMIN/VENDEDOR apenas (ESTOQUISTA não acessa) ──
async def test_estoquista_nao_acessa_clientes(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, _vendedor, estoquista = rbac_client
    resp = await client.get("/clientes", headers=_headers(estoquista))
    assert resp.status_code == 403, resp.text
    assert resp.json()["type"] == "https://amactive.dev/errors/acesso-negado"


async def test_vendedor_acessa_clientes(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, vendedor, _estoquista = rbac_client
    resp = await client.get("/clientes", headers=_headers(vendedor))
    assert resp.status_code == 200, resp.text


# ── Fornecedores: ADMIN/ESTOQUISTA apenas (VENDEDOR não acessa) ──
async def test_vendedor_nao_acessa_fornecedores(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, vendedor, _estoquista = rbac_client
    resp = await client.get("/fornecedores", headers=_headers(vendedor))
    assert resp.status_code == 403, resp.text
    assert resp.json()["type"] == "https://amactive.dev/errors/acesso-negado"


async def test_estoquista_acessa_fornecedores(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, _vendedor, estoquista = rbac_client
    resp = await client.get("/fornecedores", headers=_headers(estoquista))
    assert resp.status_code == 200, resp.text


# ── Relatórios/Dashboard: apenas ADMIN ──
async def test_vendedor_nao_acessa_relatorios(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, vendedor, _estoquista = rbac_client
    resp = await client.get("/dashboard/resumo", headers=_headers(vendedor))
    assert resp.status_code == 403, resp.text
    assert resp.json()["type"] == "https://amactive.dev/errors/acesso-negado"


async def test_estoquista_nao_acessa_relatorios(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, _vendedor, estoquista = rbac_client
    resp = await client.get("/dashboard/resumo", headers=_headers(estoquista))
    assert resp.status_code == 403, resp.text


# ── Sem token: continua 401 (autenticação, não autorização) ──
async def test_sem_token_e_401_nao_403(
    rbac_client: tuple[AsyncClient, UsuarioModel, UsuarioModel],
) -> None:
    client, _vendedor, _estoquista = rbac_client
    resp = await client.get("/clientes")
    assert resp.status_code == 401, resp.text
