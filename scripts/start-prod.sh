#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export ENGINE_URL="${ENGINE_URL:-http://127.0.0.1:8764}"
PORT="${PORT:-43124}"

cd "$ROOT/server"
if [[ -x .venv/bin/python ]]; then
  PY=".venv/bin/python"
else
  PY="python3"
fi
"$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8764 &
API_PID=$!
trap 'kill "$API_PID" 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8764/health >/dev/null; then
    break
  fi
  sleep 0.25
done

cd "$ROOT/web"
if [[ -x node_modules/.bin/next ]]; then
  exec node_modules/.bin/next start --hostname 0.0.0.0 --port "$PORT"
fi
exec npx next start --hostname 0.0.0.0 --port "$PORT"
