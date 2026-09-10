"""Infraestrutura de acesso a dados compartilhada (SQLAlchemy engine/session).

Ver docs/SDD.md ADR-003: o schema é gerenciado por migrations SQL puro em
/migrations — SQLAlchemy aqui é usado apenas como camada de acesso a dados,
nunca para gerar/versionar schema (sem Base.metadata.create_all() em uso).

Scaffold mínimo — sem modelos de domínio ainda.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from amactive.core.config import settings


class Base(DeclarativeBase):
    """Base declarativa compartilhada pelos modelos ORM de todos os contextos."""


engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency do FastAPI — fornece uma sessão por request."""
    async with async_session_factory() as session:
        yield session
