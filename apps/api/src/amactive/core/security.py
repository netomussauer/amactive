"""Segurança cross-cutting: hashing de senha (bcrypt), JWT (PyJWT) e
autorização por papel (RBAC).

TODO (Identidade & Acesso — ver docs/SDD.md ADR-007): esta é uma
autenticação **mínima e stateless** suficiente para o MVP local — o
suficiente para satisfazer a rastreabilidade obrigatória de `usuario_id` em
`pedido`/`movimentacao_estoque`. NÃO implementado (ok para uma fase futura,
não bloqueia o MVP local):
  - Revogação de token / refresh token / logout.
  - Recuperação de senha por e-mail ("esqueci minha senha") — o reset
    administrativo direto (ADMIN redefine a senha de qualquer usuário sem
    precisar da senha antiga) já existe via `PATCH /usuarios/{id}/senha`,
    ver `contexts/identidade/infrastructure/api/router.py`.

Resolvido (não é mais TODO): `get_current_user` revalida `usuario.ativo`
contra o banco a cada request (não confia apenas no claim do JWT) — um
usuário desativado perde o acesso já na próxima chamada, sem precisar
esperar o token expirar (até `jwt_expires_minutes`). Cadastro de usuários
via API também já existe (`POST /usuarios`, ADMIN apenas) — deixou de ser
feito apenas via seed de desenvolvimento (`migrations/000002_seed_dev.up.sql`,
que continua existindo só para permitir o primeiro login local).
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from amactive.core.config import settings
from amactive.shared_kernel.database import get_db_session
from amactive.shared_kernel.exceptions import AcessoNegado, NaoAutorizado

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_senha(senha_texto_plano: str) -> str:
    """Gera o hash bcrypt de uma senha em texto plano."""
    return bcrypt.hashpw(senha_texto_plano.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha_texto_plano: str, senha_hash: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash armazenado."""
    return bcrypt.checkpw(senha_texto_plano.encode("utf-8"), senha_hash.encode("utf-8"))


@dataclass(frozen=True)
class CurrentUser:
    """Usuário autenticado, extraído (sem consulta ao banco) das claims do JWT."""

    id: UUID
    nome: str
    email: str
    papel: str


def criar_access_token(*, usuario_id: UUID, nome: str, email: str, papel: str) -> str:
    """Emite um JWT assinado (HS256) com validade `settings.jwt_expires_minutes`."""
    agora = int(time.time())
    payload = {
        "sub": str(usuario_id),
        "nome": nome,
        "email": email,
        "papel": papel,
        "iat": agora,
        "exp": agora + settings.jwt_expires_minutes * 60,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> CurrentUser:
    """Dependency do FastAPI — decodifica o Bearer token, revalida que o
    usuário ainda existe e está `ativo=true` no banco, e injeta o usuário
    atual.

    A revalidação de `ativo` custa uma consulta a mais por request
    autenticado — aceitável dado o volume baixo do sistema (ver
    docs/avaliacao-integracao-nuvemshop.md), sem cache adicional por ora.
    Um usuário inexistente ou inativo recebe o mesmo erro (`NaoAutorizado`,
    401) que um token ausente/inválido — do ponto de vista do cliente,
    "sessão inválida" é a mensagem correta nos dois casos, sem vazar se o
    problema é o token em si ou o estado da conta.

    Usada em todos os routers protegidos (todos exceto `/auth/login`, `/health`
    e `/metrics`), conforme `security: [bearerAuth: []]` global em
    docs/openapi.yaml.
    """
    if credentials is None:
        raise NaoAutorizado("Token de autenticação ausente.")
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise NaoAutorizado("Token de autenticação inválido ou expirado.") from exc

    usuario_id = UUID(payload["sub"])
    resultado = await session.execute(
        text("SELECT ativo FROM usuario WHERE id = :usuario_id"),
        {"usuario_id": str(usuario_id)},
    )
    linha = resultado.first()
    if linha is None or not linha.ativo:
        raise NaoAutorizado("Sessão inválida.")

    return CurrentUser(
        id=usuario_id,
        nome=payload.get("nome", ""),
        email=payload.get("email", ""),
        papel=payload.get("papel", ""),
    )


def requer_papel(*papeis_permitidos: str) -> Callable[..., Awaitable[CurrentUser]]:
    """Factory de dependency do FastAPI que restringe um endpoint (ou grupo
    de endpoints) a um subconjunto de papéis (RBAC — ver matriz de permissões
    em docs/openapi.yaml).

    Reaproveita `get_current_user` internamente (autenticação continua
    obrigatória) e levanta `AcessoNegado` (403) se `current_user.papel` não
    estiver entre `papeis_permitidos`.

    Uso: `Depends(requer_papel("ADMIN", "ESTOQUISTA"))` — como dependency de
    um endpoint específico (`dependencies=[...]` do decorator) ou como o
    próprio parâmetro que injeta o `CurrentUser`, quando o handler também
    precisa do usuário autenticado (ex.: para gravar `usuario_id`).

    Para endpoints que qualquer papel autenticado pode acessar (tipicamente
    leituras/GET), não use esta factory — a autenticação sozinha já é
    suficiente, então use `Depends(get_current_user)` diretamente.
    """
    permitidos = frozenset(papeis_permitidos)

    async def _verificar_papel(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.papel not in permitidos:
            raise AcessoNegado(
                f"Este recurso requer um dos papéis: {', '.join(sorted(permitidos))}."
            )
        return current_user

    return _verificar_papel
