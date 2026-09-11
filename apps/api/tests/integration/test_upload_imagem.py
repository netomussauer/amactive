"""Teste de integração ponta a ponta (ASGI in-process) do fluxo de
upload/gerenciamento de imagens de produto — contra o Postgres de teste real
e um diretório de disco isolado por teste (via monkeypatch em
`settings.uploads_dir`, lido por `LocalDiskArmazenamentoDeImagem` a cada
request). Usa o usuário admin criado por
`migrations/000002_seed_dev.up.sql` (ver test_api_fluxo_completo.py)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from amactive.core.config import settings
from amactive.main import app
from amactive.shared_kernel.database import get_db_session

pytestmark = pytest.mark.integration

# Menor PNG válido possível (1x1 pixel transparente) — suficiente para
# exercitar a validação de content-type/tamanho sem depender de um asset
# real no repositório.
_PNG_MINIMO = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def _uploads_dir_isolado(tmp_path, monkeypatch):
    """Isola cada execução em um diretório temporário — evita gravar no
    volume real de uploads e permite reexecuções limpas da suíte."""
    monkeypatch.setattr(settings, "uploads_dir", str(tmp_path))


async def _autenticar(client: AsyncClient) -> dict[str, str]:
    resp = await client.post(
        "/auth/login", json={"email": "admin@amactive.dev", "senha": "amactive123"}
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_fluxo_completo_upload_e_gerenciamento_de_imagens(test_engine, tmp_path) -> None:
    session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)

    async def _override_get_db_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = _override_get_db_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            headers = await _autenticar(client)

            produto_resp = await client.post(
                "/produtos",
                json={"nome": "Top Imagem Teste", "marca": "AMACTIVE"},
                headers=headers,
            )
            assert produto_resp.status_code == 201, produto_resp.text
            produto_id = produto_resp.json()["id"]

            variante_resp = await client.post(
                f"/produtos/{produto_id}/variantes",
                json={"tamanho": "M", "cor": "Preto", "preco_venda": "79.90"},
                headers=headers,
            )
            assert variante_resp.status_code == 201, variante_resp.text

            # Cor inexistente entre as variantes do produto -> 422.
            cor_invalida_resp = await client.post(
                f"/produtos/{produto_id}/imagens",
                data={"cor": "Verde"},
                files={"arquivo": ("foto.png", _PNG_MINIMO, "image/png")},
                headers=headers,
            )
            assert cor_invalida_resp.status_code == 422
            assert cor_invalida_resp.json()["type"] == "https://amactive.dev/errors/erro-validacao"

            # Tipo de arquivo não suportado -> 422.
            tipo_invalido_resp = await client.post(
                f"/produtos/{produto_id}/imagens",
                data={"cor": "Preto"},
                files={"arquivo": ("foto.pdf", b"%PDF-1.4", "application/pdf")},
                headers=headers,
            )
            assert tipo_invalido_resp.status_code == 422

            # Upload válido, primeira imagem da cor -> principal automática,
            # cor normalizada para a grafia exata da variante ("Preto").
            upload1_resp = await client.post(
                f"/produtos/{produto_id}/imagens",
                data={"cor": "preto"},
                files={"arquivo": ("foto1.png", _PNG_MINIMO, "image/png")},
                headers=headers,
            )
            assert upload1_resp.status_code == 201, upload1_resp.text
            imagem1 = upload1_resp.json()
            assert imagem1["cor"] == "Preto"
            assert imagem1["principal"] is True
            assert imagem1["ordem"] == 0
            assert imagem1["url"].startswith(f"/media/produtos/{produto_id}/")

            arquivo_fisico1 = tmp_path / imagem1["url"].removeprefix("/media/")
            assert arquivo_fisico1.exists()

            # Segunda imagem da mesma cor -> não é principal, ordem seguinte.
            upload2_resp = await client.post(
                f"/produtos/{produto_id}/imagens",
                data={"cor": "Preto"},
                files={"arquivo": ("foto2.png", _PNG_MINIMO, "image/png")},
                headers=headers,
            )
            assert upload2_resp.status_code == 201, upload2_resp.text
            imagem2 = upload2_resp.json()
            assert imagem2["principal"] is False
            assert imagem2["ordem"] == 1

            listagem_resp = await client.get(
                f"/produtos/{produto_id}/imagens", params={"cor": "Preto"}, headers=headers
            )
            assert listagem_resp.status_code == 200
            assert [i["id"] for i in listagem_resp.json()["data"]] == [
                imagem1["id"],
                imagem2["id"],
            ]

            # Define a segunda como principal -> desmarca a primeira
            # (índice único parcial não pode ser violado).
            principal_resp = await client.patch(
                f"/produtos/{produto_id}/imagens/{imagem2['id']}/principal", headers=headers
            )
            assert principal_resp.status_code == 200, principal_resp.text
            assert principal_resp.json()["principal"] is True

            listagem2_resp = await client.get(
                f"/produtos/{produto_id}/imagens", params={"cor": "Preto"}, headers=headers
            )
            principais = {i["id"]: i["principal"] for i in listagem2_resp.json()["data"]}
            assert principais[imagem1["id"]] is False
            assert principais[imagem2["id"]] is True

            # Reordena a primeira imagem.
            ordem_resp = await client.patch(
                f"/produtos/{produto_id}/imagens/{imagem1['id']}",
                json={"ordem": 5},
                headers=headers,
            )
            assert ordem_resp.status_code == 200, ordem_resp.text
            assert ordem_resp.json()["ordem"] == 5

            # Remove a imagem: registro some do banco E o arquivo físico é
            # apagado do disco.
            remover_resp = await client.delete(
                f"/produtos/{produto_id}/imagens/{imagem1['id']}", headers=headers
            )
            assert remover_resp.status_code == 204
            assert not arquivo_fisico1.exists()

            listagem3_resp = await client.get(f"/produtos/{produto_id}/imagens", headers=headers)
            assert [i["id"] for i in listagem3_resp.json()["data"]] == [imagem2["id"]]

            # Produto inexistente -> 404 (antes de qualquer validação de
            # cor/arquivo).
            produto_inexistente_resp = await client.post(
                f"/produtos/{uuid4()}/imagens",
                data={"cor": "Preto"},
                files={"arquivo": ("foto.png", _PNG_MINIMO, "image/png")},
                headers=headers,
            )
            assert produto_inexistente_resp.status_code == 404

            # Imagem inexistente para o produto -> 404.
            imagem_inexistente_resp = await client.delete(
                f"/produtos/{produto_id}/imagens/{uuid4()}", headers=headers
            )
            assert imagem_inexistente_resp.status_code == 404
    finally:
        app.dependency_overrides.clear()
