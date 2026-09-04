#!/usr/bin/env bash
# Runs backend (uvicorn --reload), the reel-processing worker, and frontend
# (next dev) together. Ctrl+C stops all three.
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -x "$ROOT_DIR/backend/.venv/bin/uvicorn" ]; then
  echo "backend/.venv missing. Run: cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt" >&2
  exit 1
fi
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "frontend/node_modules missing. Run: cd frontend && npm install" >&2
  exit 1
fi

backend_pid=""
worker_pid=""
frontend_pid=""

cleanup() {
  echo "Stopping..."
  [ -n "$backend_pid" ] && kill -- "-$backend_pid" 2>/dev/null
  [ -n "$worker_pid" ] && kill -- "-$worker_pid" 2>/dev/null
  [ -n "$frontend_pid" ] && kill -- "-$frontend_pid" 2>/dev/null
  # ponytail: `next dev` spawns a detached `next-server` child that survives
  # killing its own process group, so name-match it directly as a fallback.
  pkill -f "uvicorn app\.main:app" 2>/dev/null
  pkill -f "app\.workers\.run_worker" 2>/dev/null
  pkill -f "next-server \(v" 2>/dev/null
}
trap cleanup EXIT INT TERM

(cd "$ROOT_DIR/backend" && exec .venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000) &
backend_pid=$!

# Without this, nothing ever consumes the "reels" RQ queue — DM'd reels sit
# at status=queued forever with no error, since enqueueing itself succeeds.
(cd "$ROOT_DIR/backend" && exec .venv/bin/python -m app.workers.run_worker) &
worker_pid=$!

(cd "$ROOT_DIR/frontend" && exec npm run dev) &
frontend_pid=$!

wait
