"""Testes unitários de `AutenticarUsuarioUseCase` — foco no custo constante do
login (sem enumeração de e-mails por tempo de resposta)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from amactive.contexts.identidade.application.use_cases import autenticar_usuario
from amactive.contexts.identidade.application.use_cases.autenticar_usuario import (
    AutenticarUsuarioUseCase,
)
from amactive.contexts.identidade.domain.entities import PapelUsuario, Usuario
from amactive.contexts.identidade.domain.exceptions import CredenciaisInvalidas
from amactive.core.security import hash_senha

pytestmark = pytest.mark.unit

_SENHA = "senha-correta-123"


def _usuario(*, ativo: bool = True) -> Usuario:
    return Usuario(
        id=uuid4(),
        nome="Ana",
        email="ana@amactive.dev",
        senha_hash=hash_senha(_SENHA),
        papel=PapelUsuario.VENDEDOR,
        ativo=ativo,
        criado_em=datetime.now(UTC),
    )


class _RepoFake:
    def __init__(self, usuario: Usuario | None) -> None:
        self._usuario = usuario

    async def buscar_por_email(self, email: str) -> Usuario | None:
        return self._usuario


@pytest.fixture
def chamadas_bcrypt(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Espia `verificar_senha` do módulo do use case, registrando o hash contra
    o qual cada verificação foi feita, e delega à implementação real."""
    original = autenticar_usuario.verificar_senha
    hashes: list[str] = []

    def _espiao(senha: str, senha_hash: str) -> bool:
        hashes.append(senha_hash)
        return original(senha, senha_hash)

    monkeypatch.setattr(autenticar_usuario, "verificar_senha", _espiao)
    return hashes


async def test_login_valido_retorna_token() -> None:
    resultado = await AutenticarUsuarioUseCase(_RepoFake(_usuario())).executar(
        email="ana@amactive.dev", senha=_SENHA
    )

    assert resultado.token_type == "bearer"
    assert resultado.access_token


async def test_email_inexistente_ainda_executa_bcrypt_e_falha(
    chamadas_bcrypt: list[str],
) -> None:
    with pytest.raises(CredenciaisInvalidas):
        await AutenticarUsuarioUseCase(_RepoFake(None)).executar(
            email="ninguem@amactive.dev", senha="qualquer-senha"
        )

    # O custo de bcrypt foi pago contra o hash descartável — sem isso, o
    # tempo de resposta revelaria que o e-mail não existe.
    assert chamadas_bcrypt == [autenticar_usuario._HASH_SENHA_DESCARTAVEL]


async def test_usuario_inativo_ainda_executa_bcrypt_e_falha(
    chamadas_bcrypt: list[str],
) -> None:
    with pytest.raises(CredenciaisInvalidas):
        await AutenticarUsuarioUseCase(_RepoFake(_usuario(ativo=False))).executar(
            email="ana@amactive.dev", senha=_SENHA
        )

    # Mesmo com a senha CORRETA, um usuário inativo não entra — e o custo de
    # bcrypt é o do hash descartável (não o do hash real, que nem é lido).
    assert chamadas_bcrypt == [autenticar_usuario._HASH_SENHA_DESCARTAVEL]


async def test_senha_errada_falha_com_a_mesma_mensagem(chamadas_bcrypt: list[str]) -> None:
    usuario = _usuario()

    with pytest.raises(CredenciaisInvalidas) as exc_info:
        await AutenticarUsuarioUseCase(_RepoFake(usuario)).executar(
            email="ana@amactive.dev", senha="senha-errada"
        )

    assert chamadas_bcrypt == [usuario.senha_hash]
    # Mensagem idêntica à dos outros dois caminhos: nada distingue "e-mail
    # inexistente", "inativo" e "senha errada" para quem está de fora.
    assert str(exc_info.value) == "E-mail ou senha inválidos."
