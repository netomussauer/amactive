#!/usr/bin/env bash
# Regenera constraints.txt: resolve as versões MAIS NOVAS permitidas pelo
# pyproject.toml, roda a suíte completa contra elas e só então grava o arquivo.
# Rodar em Linux/WSL, a partir de apps/api (ou de qualquer lugar). Uso:
#   ./regenerar-constraints.sh
# Depois: revise `git diff constraints.txt` e commite.
set -euo pipefail

API="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$(mktemp -d)/venv"
NOVO="$(mktemp)"
trap 'rm -rf "$(dirname "$VENV")" "$NOVO"' EXIT

echo ">>> resolvendo do zero (sem constraints) em venv temporário"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --quiet --upgrade pip
"$VENV/bin/pip" install --quiet -e "$API[dev]"
# Filtra o próprio pacote (`-e ...`/`amactive-api`) e linhas de comentário que o
# `pip freeze` imprime fora de um repositório git ("# Editable install with no
# version control ...") — sem isso elas vazariam para o cabeçalho do arquivo.
"$VENV/bin/pip" freeze 2>/dev/null | grep -viE '^(-e |#|amactive)' | LC_ALL=C sort > "$NOVO"

echo ">>> validando o conjunto novo: ruff, mypy e a suíte COMPLETA (unit + integração)"
(cd "$API" && "$VENV/bin/ruff" check . && "$VENV/bin/mypy" src && "$VENV/bin/python" -m pytest -q)

echo ">>> gravando constraints.txt (cabeçalho preservado)"
{
  grep '^#' "$API/constraints.txt"
  cat "$NOVO"
} > "$API/constraints.txt.novo"
mv "$API/constraints.txt.novo" "$API/constraints.txt"

echo ">>> concluído. O que mudou:"
git -C "$API" --no-pager diff --stat -- constraints.txt || true
