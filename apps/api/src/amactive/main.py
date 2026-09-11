"""Ponto de entrada da aplicação FastAPI (camada de Frameworks).

Registra os routers de cada bounded context, os exception handlers globais
(RFC 7807 — ver docs/SDD.md §3.2) e o health check. Nenhuma regra de negócio
vive aqui — ver docs/SDD.md §1.4 (Clean Architecture por contexto).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text

from amactive.contexts.cadastros.infrastructure.api.router import router as cadastros_router
from amactive.contexts.catalogo_estoque.infrastructure.api.router import (
    router as catalogo_estoque_router,
)
from amactive.contexts.identidade.infrastructure.api.router import router as identidade_router
from amactive.contexts.relatorios.infrastructure.api.router import router as relatorios_router
from amactive.contexts.vendas.infrastructure.api.router import router as vendas_router
from amactive.core.config import settings
from amactive.shared_kernel.database import engine
from amactive.shared_kernel.exceptions import DomainError

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de controle de estoque e vendas da AMACTIVE. Ver docs/openapi.yaml.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")


def _problem_details(
    *, status_code: int, title: str, type_slug: str, detail: str, instance: str
) -> dict[str, object]:
    return {
        "type": f"https://amactive.dev/errors/{type_slug}",
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": instance,
    }


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    """Traduz qualquer exceção de domínio (de qualquer contexto) para o
    formato RFC 7807 Problem Details definido em docs/SDD.md §3.2 /
    docs/openapi.yaml `ProblemDetails`."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_problem_details(
            status_code=exc.status_code,
            title=exc.title,
            type_slug=exc.type_slug,
            detail=str(exc),
            instance=request.url.path,
        ),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Garante que erros de validação do Pydantic (422 nativo do FastAPI)
    também sigam o contrato ProblemDetails, em vez do formato padrão do
    FastAPI."""
    detail = "; ".join(
        f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}" for err in exc.errors()
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_problem_details(
            status_code=422,
            title="Dados de entrada inválidos",
            type_slug="erro-validacao",
            detail=detail or "Payload inválido.",
            instance=request.url.path,
        ),
    )


app.include_router(identidade_router)
app.include_router(catalogo_estoque_router)
app.include_router(vendas_router)
app.include_router(cadastros_router)
app.include_router(relatorios_router)

# Serve as imagens de produto gravadas em disco local (ver
# catalogo_estoque/infrastructure/storage.py e docs/data-model.md decisão
# #13). O diretório é criado no startup caso ainda não exista (primeira
# execução local fora do Docker, ou volume Docker ainda vazio).
Path(settings.uploads_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.uploads_dir), name="media")


@app.get("/health", tags=["Infra"])
async def health() -> dict[str, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:  # noqa: BLE001 — health check nunca deve vazar detalhes internos
        db_status = "erro"
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "service": settings.app_name,
        "database": db_status,
    }
