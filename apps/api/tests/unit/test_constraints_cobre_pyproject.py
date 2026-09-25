"""Guarda do `constraints.txt`: toda dependência declarada no `pyproject.toml`
(runtime e `[dev]`) precisa estar travada com `==` lá. Sem isto, alguém adiciona
um pacote novo, esquece de regenerar o arquivo e o pacote volta a ser resolvido
na versão mais nova a cada build (o problema que o lockfile existe para evitar).

Não valida os pacotes TRANSITIVOS (isso é o que `./regenerar-constraints.sh`
garante); só que nada declarado ficou de fora."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_RAIZ_API = Path(__file__).resolve().parents[2]


def _normalizar(nome: str) -> str:
    return re.sub(r"[-_.]+", "-", nome).lower()


def _nome_do_requisito(requisito: str) -> str:
    # "uvicorn[standard]>=0.30" -> "uvicorn"; "sqlalchemy[asyncio]>=2.0,<2.1" -> "sqlalchemy"
    return _normalizar(re.split(r"[\s\[<>=!~;]", requisito, maxsplit=1)[0])


def test_toda_dependencia_declarada_esta_travada_no_constraints() -> None:
    pyproject = _RAIZ_API / "pyproject.toml"
    constraints = _RAIZ_API / "constraints.txt"
    if not pyproject.is_file() or not constraints.is_file():
        pytest.skip("pyproject.toml/constraints.txt ausentes neste workspace")

    projeto = tomllib.loads(pyproject.read_text(encoding="utf-8"))["project"]
    declaradas = {_nome_do_requisito(r) for r in projeto["dependencies"]}
    declaradas |= {_nome_do_requisito(r) for r in projeto["optional-dependencies"]["dev"]}

    travadas: dict[str, str] = {}
    for linha in constraints.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#"):
            continue
        assert "==" in linha, f"constraints.txt deve travar com '==': {linha!r}"
        nome, versao = linha.split("==", maxsplit=1)
        travadas[_normalizar(nome)] = versao

    faltando = sorted(declaradas - set(travadas))
    assert not faltando, (
        f"dependências declaradas no pyproject.toml e ausentes do constraints.txt: {faltando} "
        "— rode ./regenerar-constraints.sh e commite o arquivo"
    )
