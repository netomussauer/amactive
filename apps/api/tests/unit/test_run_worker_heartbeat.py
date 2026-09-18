"""Testes do heartbeat de liveness do worker — ver `run_worker._registrar_heartbeat`
e o `livenessProbe` de infra/k8s/worker/deployment.yaml."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from amactive.scripts.run_worker import _registrar_heartbeat

pytestmark = pytest.mark.unit


def test_cria_o_arquivo_quando_nao_existe(tmp_path: Path) -> None:
    arquivo = tmp_path / "heartbeat"

    _registrar_heartbeat(arquivo)

    assert arquivo.exists()


def test_renova_o_mtime_quando_o_arquivo_ja_existe(tmp_path: Path) -> None:
    arquivo = tmp_path / "heartbeat"
    arquivo.touch()
    antigo = time.time() - 3600
    os.utime(arquivo, (antigo, antigo))

    _registrar_heartbeat(arquivo)

    assert time.time() - arquivo.stat().st_mtime < 60


def test_diretorio_inexistente_nao_levanta(tmp_path: Path) -> None:
    # Fora do container (ex.: Windows sem /tmp) o heartbeat é só ignorado.
    _registrar_heartbeat(tmp_path / "nao-existe" / "heartbeat")
