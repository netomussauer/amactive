"""Schemas Pydantic compartilhados entre contextos (envelope de paginação, erros).

Ver docs/SDD.md §3.2 (Padrão de Erros) e §3.3 (Paginação Padrão).
"""

from __future__ import annotations

from pydantic import BaseModel


class Pagination(BaseModel):
    total: int
    page: int
    per_page: int


class ProblemDetails(BaseModel):
    """RFC 7807 Problem Details — ver docs/openapi.yaml `ProblemDetails`."""

    type: str
    title: str
    status: int
    detail: str
    instance: str
