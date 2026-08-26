#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$ROOT/server/data/lim" "$ROOT/server/data/drawings"

wait_http() {
  local url="$1"
  local attempts="${2:-40}"
  local delay="${3:-0.25}"
  local i
  for i in $(seq 1 "$attempts"); do
    if curl -sf "$url" >/dev/null; then
      return 0
    fi
    sleep "$delay"
  done
  echo "timed out waiting for $url" >&2
  return 1
}

if ! curl -sf http://127.0.0.1:8764/health >/dev/null; then
  (
    cd "$ROOT/server"
    exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8764
  ) >/tmp/auckland-api.log 2>&1 &
fi
wait_http http://127.0.0.1:8764/health 40 0.25

if ! curl -sf http://127.0.0.1:43124 >/dev/null; then
  (
    cd "$ROOT/web"
    export ENGINE_URL="${ENGINE_URL:-http://127.0.0.1:8764}"
    exec ./node_modules/.bin/next dev --hostname 0.0.0.0 --port 43124
  ) >/tmp/auckland-web.log 2>&1 &
fi
wait_http http://127.0.0.1:43124 60 0.5
