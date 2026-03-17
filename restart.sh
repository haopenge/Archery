#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".env" ]; then
    database_url=$(grep -E '^DATABASE_URL=' .env | head -n 1 | cut -d= -f2-)
    cache_url=$(grep -E '^CACHE_URL=' .env | head -n 1 | cut -d= -f2-)
    if echo "$database_url" | grep -q '@mysql:'; then
        export DATABASE_URL="${database_url//@mysql:/@127.0.0.1:}"
    fi
    if echo "$cache_url" | grep -q '^redis://redis:'; then
        cache_auth=$(echo "$cache_url" | sed -n 's/.*PASSWORD=\([^&]*\).*/\1/p')
        if [ -n "$cache_auth" ]; then
            export CACHE_URL="redis://:${cache_auth}@127.0.0.1:6379/0"
        else
            export CACHE_URL="redis://127.0.0.1:6379/0"
        fi
    fi
fi

source .venv/bin/activate

# 检查 supervisord 是否正在运行
if [ -f supervisor.sock ]; then
    echo "Supervisord is running. Restarting all services..."
    # 重启所有受控进程（archery, qcluster）
    supervisorctl -c supervisord.conf restart all
else
    echo "Supervisord is not running. Starting services..."
    # 启动服务
    ./startup.sh
fi
