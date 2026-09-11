FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src
COPY docker-entrypoint.sh ./

RUN pip install --no-cache-dir . \
    && chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# O entrypoint aplica migrations pendentes (amactive.scripts.apply_migrations)
# antes de subir a API — útil para `docker compose up` de ponta a ponta sem
# passo manual. Ver docs/SDD.md §7 (ferramenta de migração ainda não fixada
# definitivamente — este é o script equivalente adotado para o MVP local).
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "amactive.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
