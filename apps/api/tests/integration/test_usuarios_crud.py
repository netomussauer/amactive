"""Teste de integração ponta a ponta (ASGI in-process, Postgres de teste
real) do CRUD administrativo de usuários (`/usuarios`, ADMIN apenas — ver
docs/SDD.md ADR-007) e da revalidação de `usuario.ativo` a cada request
(Escopo 2 — `core/security.get_current_user`).

Diferente da maioria dos outros arquivos de integração (que usam uma sessão
"real" por request via `test_engine`), este arquivo reusa a sessão
transacional isolada por teste (`db_session`, com SAVEPOINT — ver
docstring de `tests/integration/conftest.py`) como override de
`get_db_session` durante toda a duração de cada teste. Isso é necessário
porque os testes de salvaguarda do "último ADMIN ativo" precisam poder
desativar até o usuário admin de seed (`admin@amactive.dev`) para forçar o
cenário de "só resta um ADMIN ativo" — algo que não pode vazar para os
demais arquivos de teste (que dependem do login desse admin de seed
continuar funcionando)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


async def _login_completo(
    client: AsyncClient, email: str, senha: str
) -> tuple[dict[str, str], str]:
    resp = await client.post("/auth/login", json={"email": email, "senha": senha})
    assert resp.status_code == 200, resp.text
    corpo = resp.json()
    return {"Authorization": f"Bearer {corpo['access_token']}"}, corpo["usuario"]["id"]


async def _admin_headers(client: AsyncClient) -> dict[str, str]:
    headers, _ = await _login_completo(client, "admin@amactive.dev", "amactive123")
    return headers


# ── CRUD completo ──
async def test_crud_completo_de_usuarios(client: AsyncClient) -> None:
    admin_headers = await _admin_headers(client)
    email = f"crud-{uuid4().hex[:8]}@amactive.dev"

    criar_resp = await client.post(
        "/usuarios",
        json={"nome": "Usuário CRUD", "email": email, "senha": "senha12345", "papel": "VENDEDOR"},
        headers=admin_headers,
    )
    assert criar_resp.status_code == 201, criar_resp.text
    usuario = criar_resp.json()
    assert usuario["email"] == email
    assert usuario["ativo"] is True
    assert "senha" not in usuario
    assert "senha_hash" not in usuario
    usuario_id = usuario["id"]

    obter_resp = await client.get(f"/usuarios/{usuario_id}", headers=admin_headers)
    assert obter_resp.status_code == 200, obter_resp.text
    assert obter_resp.json()["nome"] == "Usuário CRUD"

    listar_resp = await client.get("/usuarios", headers=admin_headers)
    assert listar_resp.status_code == 200, listar_resp.text
    corpo_lista = listar_resp.json()
    assert any(u["id"] == usuario_id for u in corpo_lista["data"])
    assert "pagination" in corpo_lista

    atualizar_resp = await client.put(
        f"/usuarios/{usuario_id}",
        json={"nome": "Usuário CRUD Atualizado", "papel": "ESTOQUISTA", "ativo": True},
        headers=admin_headers,
    )
    assert atualizar_resp.status_code == 200, atualizar_resp.text
    assert atualizar_resp.json()["nome"] == "Usuário CRUD Atualizado"
    assert atualizar_resp.json()["papel"] == "ESTOQUISTA"

    senha_resp = await client.patch(
        f"/usuarios/{usuario_id}/senha", json={"senha": "nova-senha-999"}, headers=admin_headers
    )
    assert senha_resp.status_code == 204, senha_resp.text

    novo_login = await client.post("/auth/login", json={"email": email, "senha": "nova-senha-999"})
    assert novo_login.status_code == 200, novo_login.text

    deletar_resp = await client.delete(f"/usuarios/{usuario_id}", headers=admin_headers)
    assert deletar_resp.status_code == 204, deletar_resp.text

    obter_apos_delete = await client.get(f"/usuarios/{usuario_id}", headers=admin_headers)
    assert obter_apos_delete.status_code == 200, obter_apos_delete.text
    assert obter_apos_delete.json()["ativo"] is False

    obter_inexistente = await client.get(f"/usuarios/{uuid4()}", headers=admin_headers)
    assert obter_inexistente.status_code == 404, obter_inexistente.text


async def test_criar_usuario_com_email_duplicado_retorna_409(client: AsyncClient) -> None:
    admin_headers = await _admin_headers(client)
    email = f"dup-{uuid4().hex[:8]}@amactive.dev"
    resp1 = await client.post(
        "/usuarios",
        json={"nome": "A", "email": email, "senha": "senha12345", "papel": "VENDEDOR"},
        headers=admin_headers,
    )
    assert resp1.status_code == 201, resp1.text

    resp2 = await client.post(
        "/usuarios",
        json={"nome": "B", "email": email, "senha": "outrasenha1", "papel": "ESTOQUISTA"},
        headers=admin_headers,
    )
    assert resp2.status_code == 409, resp2.text
    assert resp2.json()["type"] == "https://amactive.dev/errors/conflito"


# ── RBAC: apenas ADMIN acessa /usuarios ──
async def test_nao_admin_recebe_403_ao_acessar_usuarios(client: AsyncClient) -> None:
    admin_headers = await _admin_headers(client)
    email = f"vend-{uuid4().hex[:8]}@amactive.dev"
    criar = await client.post(
        "/usuarios",
        json={"nome": "Vendedor", "email": email, "senha": "senha12345", "papel": "VENDEDOR"},
        headers=admin_headers,
    )
    assert criar.status_code == 201, criar.text
    vendedor_headers, _ = await _login_completo(client, email, "senha12345")

    resp = await client.get("/usuarios", headers=vendedor_headers)
    assert resp.status_code == 403, resp.text
    assert resp.json()["type"] == "https://amactive.dev/errors/acesso-negado"


# ── Escopo 2: usuário desativado perde acesso na chamada seguinte ──
async def test_usuario_desativado_perde_acesso_na_proxima_chamada(client: AsyncClient) -> None:
    admin_headers = await _admin_headers(client)
    email = f"desat-{uuid4().hex[:8]}@amactive.dev"
    criar = await client.post(
        "/usuarios",
        json={
            "nome": "Vai Ser Desativado",
            "email": email,
            "senha": "senha12345",
            "papel": "VENDEDOR",
        },
        headers=admin_headers,
    )
    assert criar.status_code == 201, criar.text
    usuario_id = criar.json()["id"]
    usuario_headers, _ = await _login_completo(client, email, "senha12345")

    acesso_antes = await client.get("/clientes", headers=usuario_headers)
    assert acesso_antes.status_code == 200, acesso_antes.text

    desativar = await client.delete(f"/usuarios/{usuario_id}", headers=admin_headers)
    assert desativar.status_code == 204, desativar.text

    acesso_depois = await client.get("/clientes", headers=usuario_headers)
    assert acesso_depois.status_code == 401, acesso_depois.text
    assert acesso_depois.json()["type"] == "https://amactive.dev/errors/nao-autorizado"


# ── Salvaguarda do último ADMIN ativo ──
async def test_ultimo_admin_ativo_nao_pode_se_autodesativar_via_delete(
    client: AsyncClient,
) -> None:
    admin_headers, seed_admin_id = await _login_completo(
        client, "admin@amactive.dev", "amactive123"
    )

    novo_admin_email = f"novoadmin-{uuid4().hex[:8]}@amactive.dev"
    criar = await client.post(
        "/usuarios",
        json={
            "nome": "Novo Admin",
            "email": novo_admin_email,
            "senha": "senha12345",
            "papel": "ADMIN",
        },
        headers=admin_headers,
    )
    assert criar.status_code == 201, criar.text
    novo_admin_id = criar.json()["id"]
    novo_admin_headers, _ = await _login_completo(client, novo_admin_email, "senha12345")

    # Ainda há dois ADMINs ativos (seed + novo) — o novo admin desativando o
    # seed (não é auto-alvo) é permitido normalmente.
    desativar_seed = await client.delete(f"/usuarios/{seed_admin_id}", headers=novo_admin_headers)
    assert desativar_seed.status_code == 204, desativar_seed.text

    # Agora o novo admin é o único ADMIN ativo — auto-desativação bloqueada.
    autodesativar = await client.delete(f"/usuarios/{novo_admin_id}", headers=novo_admin_headers)
    assert autodesativar.status_code == 409, autodesativar.text
    assert autodesativar.json()["type"] == "https://amactive.dev/errors/conflito"

    obter = await client.get(f"/usuarios/{novo_admin_id}", headers=novo_admin_headers)
    assert obter.json()["ativo"] is True


async def test_ultimo_admin_ativo_nao_pode_rebaixar_o_proprio_papel_via_put(
    client: AsyncClient,
) -> None:
    admin_headers, seed_admin_id = await _login_completo(
        client, "admin@amactive.dev", "amactive123"
    )

    novo_admin_email = f"novoadmin2-{uuid4().hex[:8]}@amactive.dev"
    criar = await client.post(
        "/usuarios",
        json={
            "nome": "Novo Admin 2",
            "email": novo_admin_email,
            "senha": "senha12345",
            "papel": "ADMIN",
        },
        headers=admin_headers,
    )
    assert criar.status_code == 201, criar.text
    novo_admin_id = criar.json()["id"]
    novo_admin_headers, _ = await _login_completo(client, novo_admin_email, "senha12345")

    desativar_seed = await client.delete(f"/usuarios/{seed_admin_id}", headers=novo_admin_headers)
    assert desativar_seed.status_code == 204, desativar_seed.text

    rebaixar = await client.put(
        f"/usuarios/{novo_admin_id}",
        json={"nome": "Novo Admin 2", "papel": "VENDEDOR", "ativo": True},
        headers=novo_admin_headers,
    )
    assert rebaixar.status_code == 409, rebaixar.text
    assert rebaixar.json()["type"] == "https://amactive.dev/errors/conflito"

    obter = await client.get(f"/usuarios/{novo_admin_id}", headers=novo_admin_headers)
    assert obter.json()["papel"] == "ADMIN"
