"""Command: autenticar usuário por e-mail/senha e emitir um JWT."""

from __future__ import annotations

from dataclasses import dataclass

from amactive.contexts.identidade.domain.exceptions import CredenciaisInvalidas
from amactive.contexts.identidade.domain.repositories import UsuarioRepository
from amactive.core.security import criar_access_token, verificar_senha


@dataclass(frozen=True)
class LoginResultado:
    access_token: str
    token_type: str
    usuario_id: str
    nome: str
    email: str
    papel: str


class AutenticarUsuarioUseCase:
    def __init__(self, usuario_repository: UsuarioRepository) -> None:
        self._usuario_repository = usuario_repository

    async def executar(self, *, email: str, senha: str) -> LoginResultado:
        usuario = await self._usuario_repository.buscar_por_email(email)
        if usuario is None or not usuario.ativo or not verificar_senha(senha, usuario.senha_hash):
            raise CredenciaisInvalidas("E-mail ou senha inválidos.")

        token = criar_access_token(
            usuario_id=usuario.id,
            nome=usuario.nome,
            email=usuario.email,
            papel=usuario.papel.value,
        )
        return LoginResultado(
            access_token=token,
            token_type="bearer",
            usuario_id=str(usuario.id),
            nome=usuario.nome,
            email=usuario.email,
            papel=usuario.papel.value,
        )
