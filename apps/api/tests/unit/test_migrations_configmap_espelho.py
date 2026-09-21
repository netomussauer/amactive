"""Guarda do espelho manual `infra/k8s/api/migrations-configmap.yaml`.

O pod da API aplica as migrations a partir desse ConfigMap (o build context do
Dockerfile não inclui `migrations/`), mantido À MÃO — ver o cabeçalho do
próprio YAML. Este teste falha se algum `migrations/*.up.sql` (exceto o seed de
dev 000002, omitido de propósito) estiver ausente ou divergir, byte a byte,
do bloco correspondente do ConfigMap.

Pula sozinho quando os arquivos não existem (ex.: a Task de CI `python-test`
copia só `apps/api/` para o workspace, sem o restante do monorepo)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# Intencionalmente fora do ConfigMap (usuário admin com senha fraca conhecida).
_OMITIDAS_DE_PROPOSITO = {"000002_seed_dev.up.sql"}


def test_configmap_espelha_byte_a_byte_as_migrations_up() -> None:
    yaml = pytest.importorskip("yaml")
    # Resolvido sob demanda: em um workspace só com `apps/api/` o `parents[4]`
    # nem existe (ver `tests/integration/conftest.py::_migrations_dir`).
    try:
        raiz_repo = Path(__file__).resolve().parents[4]
    except IndexError:
        pytest.skip("layout do monorepo ausente neste workspace")
    migrations = raiz_repo / "migrations"
    configmap = raiz_repo / "infra" / "k8s" / "api" / "migrations-configmap.yaml"
    if not migrations.is_dir() or not configmap.is_file():
        pytest.skip("migrations/ ou infra/k8s/ ausentes neste workspace")

    documentos = [d for d in yaml.safe_load_all(configmap.read_text(encoding="utf-8")) if d]
    conteudos: dict[str, str] = documentos[0]["data"]

    esperadas = {
        arquivo.name: arquivo
        for arquivo in sorted(migrations.glob("*.up.sql"))
        if arquivo.name not in _OMITIDAS_DE_PROPOSITO
    }
    assert set(conteudos) == set(esperadas), (
        "ConfigMap e migrations/ divergem em quais arquivos existem"
    )
    for nome, arquivo in esperadas.items():
        assert conteudos[nome].encode("utf-8") == arquivo.read_bytes(), (
            f"{nome} difere do ConfigMap"
        )
