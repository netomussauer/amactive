"""Segurança cross-cutting: hashing de senha (bcrypt) e JWT (PyJWT).

TODO (Identidade & Acesso — ver docs/SDD.md ADR-007, escopo item 6 do pedido
de implementação): esta é uma autenticação **mínima e stateless** suficiente
para o MVP local — o suficiente para satisfazer a rastreabilidade obrigatória
de `usuario_id` em `pedido`/`movimentacao_estoque`. NÃO implementado (ok para
uma fase futura, não bloqueia o MVP local):
  - Autorização por papel (RBAC) por endpoint (ADMIN/VENDEDOR/ESTOQUISTA) —
    hoje qualquer usuário autenticado (token válido) pode chamar qualquer
    endpoint protegido.
  - Revogação de token / refresh token / logout.
  - Verificação de `usuario.ativo` a cada request (o claim do JWT não é
    revalidado contra o banco em cada chamada — apenas no login). Um usuário
    desativado após o login continua com o token válido até expirar.
  - Recuperação de senha, cadastro de usuários via API (feito apenas via seed
    de desenvolvimento em `migrations/000002_seed_dev.up.sql`).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from uuid import UUID

import bcrypt
import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from amactive.core.config import settings
from amactive.shared_kernel.exceptions import NaoAutorizado

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
