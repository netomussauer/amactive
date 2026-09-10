"""Ponto de entrada da aplicação FastAPI (camada de Frameworks).

Scaffold mínimo: expõe /health e prepara o app para o registro dos routers
de cada bounded context (a cargo do dev-expert-fullcycle). Nenhuma regra de
negócio vive aqui — ver docs/SDD.md §1.4 (Clean Architecture por contexto).
"""

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from amactive.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de controle de estoque e vendas da AMACTIVE. Ver docs/openapi.yaml.",
)

Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# Routers de cada bounded context serão registrados aqui, ex:
# from amactive.contexts.catalogo_estoque.infrastructure.api.router import router as catalogo_router
# app.include_router(catalogo_router, prefix="/produtos", tags=["Produtos"])


@app.get("/health", tags=["Infra"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
