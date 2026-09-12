"""Segurança cross-cutting: hashing de senha (bcrypt), JWT (PyJWT) e
autorização por papel (RBAC).

TODO (Identidade & Acesso — ver docs/SDD.md ADR-007, escopo item 6 do pedido
de implementação): esta é uma autenticação **mínima e stateless** suficiente
para o MVP local — o suficiente para satisfazer a rastreabilidade obrigatória
de `usuario_id` em `pedido`/`movimentacao_estoque`. NÃO implementado (ok para
uma fase futura, não bloqueia o MVP local):
  - Revogação de token / refresh token / logout.
  - Verificação de `usuario.ativo` a cada request (o claim do JWT não é
    revalidado contra o banco em cada chamada — apenas no login). Um usuário
    desativado após o login continua com o token válido até expirar.
  - Recuperação de senha, cadastro de usuários via API (feito apenas via seed
    de desenvolvimento em `migrations/000002_seed_dev.up.sql`).
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

from amactive.core.config import settings
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
) -> CurrentUser:
    """Dependency do FastAPI — decodifica o Bearer token e injeta o usuário atual.

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

    return CurrentUser(
        id=UUID(payload["sub"]),
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
