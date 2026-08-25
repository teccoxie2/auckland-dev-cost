#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="$ROOT/server/data"

rm -f "$DATA"/projects.sqlite "$DATA"/projects.sqlite-* \
  "$DATA"/langgraph-checkpoints.sqlite "$DATA"/langgraph-checkpoints.sqlite-*
rm -rf "$DATA/lim" "$DATA/drawings"
mkdir -p "$DATA/lim" "$DATA/drawings"

echo "Cleared project database, LIM uploads, drawings, and LangGraph checkpoints."
echo "Restart the API so it opens a new empty SQLite file."
