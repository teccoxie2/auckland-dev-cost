#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0

mkdir -p "$ROOT/server/data/lim" "$ROOT/server/data/drawings"

if ! python3 -c "import venv" 2>/dev/null; then
  sudo apt-get update
  sudo apt-get install -y python3.12-venv python3-pip
fi

python3 -m venv "$ROOT/server/.venv"
"$ROOT/server/.venv/bin/pip" install -q -r "$ROOT/server/requirements.txt"

corepack prepare pnpm@10.33.3 --activate
pnpm --dir "$ROOT/web" install --frozen-lockfile
