#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export PYTHONPATH="$PWD/..${PYTHONPATH:+:$PYTHONPATH}"

# Point this at a separate recipe storage database, never the CNF database.
: "${RECIPE_DATABASE_URL:?Set RECIPE_DATABASE_URL to your dedicated recipe database first.}"
: "${MACROCHEF_DATABASE_URL:=}"
if [[ -n "$MACROCHEF_DATABASE_URL" ]]; then
  : "${MACROCHEF_CATALOGUE_REVISION:?Set a meaningful catalogue revision for custom food data.}"
  export MACROCHEF_CATALOGUE="${MACROCHEF_CATALOGUE:-imported}"
else
  export MACROCHEF_CATALOGUE=fixture
  export MACROCHEF_CATALOGUE_REVISION=fixture-v2
  export MACROCHEF_DEMO_DB="$PWD/.demo/macrochef-fixtures-v2.sqlite3"
fi
export RECIPE_DATABASE_URL MACROCHEF_DATABASE_URL MACROCHEF_CATALOGUE_REVISION PYTHONDONTWRITEBYTECODE=1
if [[ ! -x .venv/bin/python ]]; then python3 -m venv .venv; fi
PY=.venv/bin/python
if ! "$PY" -c 'import fastapi,uvicorn,psycopg,pydantic_ai,dotenv' >/dev/null 2>&1; then
  "$PY" -m pip install -r backend/requirements-ai.txt
fi
if [[ -z "$MACROCHEF_DATABASE_URL" && ! -f "$MACROCHEF_DEMO_DB" ]]; then "$PY" -m backend.seed; fi
if [[ ! -f frontend/dist/index.html ]]; then
  echo 'Build the frontend first: (cd frontend && npm ci && npm run build).' >&2
  exit 1
fi
export RECIPE_STORE_URL="http://127.0.0.1:${MACROCHEF_RECIPE_PORT:-3028}"
PORT="${MACROCHEF_RECIPE_PORT:-3028}" HOST=127.0.0.1 node recipe/server.js &
recipe_pid=$!
cleanup() { kill "$recipe_pid" 2>/dev/null || true; wait "$recipe_pid" 2>/dev/null || true; }
trap cleanup EXIT
for _ in {1..50}; do
  if ! kill -0 "$recipe_pid" 2>/dev/null; then
    echo 'Recipe store stopped. Check its dependencies and configuration.' >&2
    exit 1
  fi
  if "$PY" -c 'from urllib.request import urlopen; from os import environ; assert urlopen(environ["RECIPE_STORE_URL"] + "/health", timeout=.3).status == 200' >/dev/null 2>&1; then
    "$PY" -m uvicorn backend.app:app --host 127.0.0.1 --port "${MACROCHEF_PORT:-8002}"
    exit
  fi
  sleep .1
done
echo 'Recipe store unavailable. Check that its database is running and recipe/schema.sql was applied.' >&2
exit 1
