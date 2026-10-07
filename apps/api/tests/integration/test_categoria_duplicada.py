"""Nome de categoria duplicado contra o Postgres real: antes, a violação de
UNIQUE (nome/slug) não era tratada e subia como 500 em texto puro — o
apiClient do frontend não conseguia fazer .json() dessa resposta e perdia o
`detail`, mostrando uma mensagem genérica no modal. Agora é um 409 (RFC 7807),
igual aos outros conflitos de unicidade da API (SKU de variante)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.contexts.catalogo_estoque.application.use_cases.categoria_use_cases import (
    CriarCategoriaCommand,
)
from amactive.contexts.catalogo_estoque.domain.exceptions import CategoriaDuplicada
from amactive.contexts.catalogo_estoque.infrastructure.persistence.repositories import (
    SqlAlchemyCategoriaRepository,
)
from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration


async def test_nome_duplicado_recusado_sem_subir_erro_interno(db_session: AsyncSession) -> None:
    repo = SqlAlchemyCategoriaRepository(db_session)
    comando = CriarCategoriaCommand(repo)

    criada = await comando.executar(nome="Calças Teste")
    assert criada.slug == "calcas-teste"
    # Protege a criação válida do rollback que a tentativa duplicada dispara
    # logo abaixo — mesmo motivo do comentário na fixture `usuario_teste`
    # em conftest.py (join_transaction_mode="create_savepoint").
    await db_session.commit()

    with pytest.raises(CategoriaDuplicada):
        await comando.executar(nome="Calças Teste")

    # A tentativa recusada não deixou uma segunda linha nem corrompeu a sessão.
    categorias = await repo.listar()
    assert sum(1 for c in categorias if c.nome == "Calças Teste") == 1


async def test_nomes_diferentes_com_mesmo_slug_tambem_sao_recusados(
    db_session: AsyncSession,
) -> None:
    # "Calças" e "CALÇAS!!" normalizam para o mesmo slug ("calcas") — o slug
    # também é UNIQUE, então a segunda precisa ser recusada mesmo com nome
    # diferente na tela.
    repo = SqlAlchemyCategoriaRepository(db_session)
    comando = CriarCategoriaCommand(repo)
    await comando.executar(nome="Calças Slug")

    with pytest.raises(CategoriaDuplicada):
        await comando.executar(nome="CALÇAS SLUG!!")


async def test_http_responde_409_em_json_nao_500_em_texto_puro(db_session: AsyncSession) -> None:
    async def _sessao_de_teste():
        yield db_session

    app.dependency_overrides[get_db_session] = _sessao_de_teste
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post(
                "/auth/login", json={"email": "admin@amactive.dev", "senha": "amactive123"}
            )
            assert login.status_code == 200, login.text
            headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

            primeira = await client.post(
                "/categorias", json={"nome": "Macacões Teste"}, headers=headers
            )
            assert primeira.status_code == 201, primeira.text

            segunda = await client.post(
                "/categorias", json={"nome": "Macacões Teste"}, headers=headers
            )
            assert segunda.status_code == 409, segunda.text
            corpo = segunda.json()  # antes do fix: levantava json.decoder.JSONDecodeError aqui
            assert corpo["type"].endswith("/conflito")
            assert "Macacões Teste" in corpo["detail"]
    finally:
        app.dependency_overrides.pop(get_db_session, None)
