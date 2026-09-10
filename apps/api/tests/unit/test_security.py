from __future__ import annotations

from uuid import uuid4

import jwt
import pytest

from amactive.core.config import settings
from amactive.core.security import criar_access_token, hash_senha, verificar_senha

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
