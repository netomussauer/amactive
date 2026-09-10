"""Utilitário de paginação compartilhado (offset/limit a partir de page/per_page)."""

from __future__ import annotations


def offset_limit(*, page: int, per_page: int) -> tuple[int, int]:
    """Converte `page` (1-based) e `per_page` em `(offset, limit)` para SQL."""
    page = max(page, 1)
    per_page = max(per_page, 1)
    return (page - 1) * per_page, per_page
