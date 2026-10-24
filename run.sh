#!/usr/bin/env bash
# Usage: ./run.sh            (live: Blockscout + mempool.space + Sapling, falls back to cache)
#        CS_OFFLINE=1 ./run.sh   (cache only: works with no internet for the showcase wallets)
set -e; cd "$(dirname "$0")"
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
exec .venv/bin/uvicorn app:app --app-dir backend --host 0.0.0.0 --port "${PORT:-8000}"
