#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

python3 -m venv "$ROOT/server/.venv"
"$ROOT/server/.venv/bin/pip" install -r "$ROOT/server/requirements.txt"

corepack prepare pnpm@10.33.3 --activate
pnpm --dir "$ROOT/web" install --frozen-lockfile
