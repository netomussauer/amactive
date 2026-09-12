from __future__ import annotations

from uuid import uuid4

import jwt
import pytest

from amactive.core.config import settings
from amactive.core.security import (
    CurrentUser,
    criar_access_token,
    hash_senha,
    requer_papel,
    verificar_senha,
)
from amactive.shared_kernel.exceptions import AcessoNegado

pytestmark = pytest.mark.unit


def test_hash_e_verificacao_de_senha() -> None:
    hash_gerado = hash_senha("senha-super-secreta")
    assert verificar_senha("senha-super-secreta", hash_gerado)
    assert not verificar_senha("senha-errada", hash_gerado)


def test_access_token_contem_claims_esperadas() -> None:
    usuario_id = uuid4()
    token = criar_access_token(
        usuario_id=usuario_id, nome="Ana", email="ana@amactive.dev", papel="ADMIN"
    )

    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

    assert payload["sub"] == str(usuario_id)
    assert payload["nome"] == "Ana"
    assert payload["email"] == "ana@amactive.dev"
    assert payload["papel"] == "ADMIN"
    assert payload["exp"] > payload["iat"]


async def test_requer_papel_permite_usuario_com_papel_permitido() -> None:
    dependency = requer_papel("ADMIN", "ESTOQUISTA")
    usuario = CurrentUser(id=uuid4(), nome="Ana", email="ana@amactive.dev", papel="ESTOQUISTA")

    resultado = await dependency(usuario)

    assert resultado is usuario


async def test_requer_papel_nega_usuario_sem_papel_permitido() -> None:
    dependency = requer_papel("ADMIN", "ESTOQUISTA")
    usuario = CurrentUser(id=uuid4(), nome="Beto", email="beto@amactive.dev", papel="VENDEDOR")

    with pytest.raises(AcessoNegado) as exc_info:
        await dependency(usuario)

    mensagem = str(exc_info.value)
    assert "ADMIN" in mensagem
    assert "ESTOQUISTA" in mensagem


async def test_requer_papel_com_papel_unico_nega_os_demais() -> None:
    dependency = requer_papel("ADMIN")
    usuario = CurrentUser(id=uuid4(), nome="Carla", email="carla@amactive.dev", papel="VENDEDOR")

    with pytest.raises(AcessoNegado):
        await dependency(usuario)
