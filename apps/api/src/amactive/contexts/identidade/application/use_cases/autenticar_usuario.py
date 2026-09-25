"""Command: autenticar usuário por e-mail/senha e emitir um JWT."""

from __future__ import annotations

from dataclasses import dataclass

from amactive.contexts.identidade.domain.exceptions import CredenciaisInvalidas
from amactive.contexts.identidade.domain.repositories import UsuarioRepository
from amactive.core.security import criar_access_token, hash_senha, verificar_senha

# Hash bcrypt de uma senha descartável, calculado uma vez no import. Usado
# quando o e-mail não existe ou o usuário está inativo: `verificar_senha`
# ainda roda (e demora o mesmo que para um usuário real), então o tempo de
# resposta do login não revela quais e-mails estão cadastrados. Sem isso, o
# caminho "usuário inexistente" retornava em microssegundos e o "senha
# errada" levava ~centenas de ms de bcrypt — enumeração de e-mails válidos
# por tempo, relevante agora que o login é alcançável pela internet.
_HASH_SENHA_DESCARTAVEL = hash_senha("senha-descartavel-nunca-valida")


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
        if usuario is None or not usuario.ativo:
            # Mesmo custo de bcrypt de um usuário real (ver
            # `_HASH_SENHA_DESCARTAVEL`); o resultado é ignorado.
            verificar_senha(senha, _HASH_SENHA_DESCARTAVEL)
            raise CredenciaisInvalidas("E-mail ou senha inválidos.")
        if not verificar_senha(senha, usuario.senha_hash):
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
