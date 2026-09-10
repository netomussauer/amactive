#!/usr/bin/env bash
set -euo pipefail

python -m amactive.scripts.apply_migrations

exec "$@"
