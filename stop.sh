#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

if supervisorctl -c supervisord.conf status >/dev/null 2>&1; then
    supervisorctl -c supervisord.conf shutdown >/dev/null 2>&1 || true
fi

PIDS="$(lsof -tiTCP:8888 -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "${PIDS}" ]; then
    kill ${PIDS} >/dev/null 2>&1 || true
    sleep 1
fi

PIDS="$(lsof -tiTCP:8888 -sTCP:LISTEN 2>/dev/null || true)"
if [ -n "${PIDS}" ]; then
    kill -9 ${PIDS} >/dev/null 2>&1 || true
fi

pkill -f "manage.py qcluster" >/dev/null 2>&1 || true
pkill -f "gunicorn.*archery.wsgi:application" >/dev/null 2>&1 || true

if lsof -tiTCP:8888 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "stop failed: port 8888 is still in use"
    exit 1
fi

echo "services stopped"
