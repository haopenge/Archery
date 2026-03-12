#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

WITH_TEMPLATES=0
if [[ "${1:-}" == "--with-templates" ]]; then
    WITH_TEMPLATES=1
fi

PYTHON_BIN="python3"
if [[ -x "./.venv/bin/python3" ]]; then
    PYTHON_BIN="./.venv/bin/python3"
elif [[ -x "./venv/bin/python3" ]]; then
    PYTHON_BIN="./venv/bin/python3"
elif [[ -x "/opt/venv4archery/bin/python3" ]]; then
    PYTHON_BIN="/opt/venv4archery/bin/python3"
elif ! python3 -c "import django" >/dev/null 2>&1; then
    echo "未找到可用的Django运行环境。"
    echo "请先准备虚拟环境后重试，例如:"
    echo "  sh admin.sh init"
    echo "或手动安装依赖后再执行本脚本。"
    exit 1
fi

run_sql() {
    local sql_file="$1"
    if [[ ! -f "$sql_file" ]]; then
        echo "SQL文件不存在: $sql_file"
        exit 1
    fi
    echo "正在导入: $sql_file"
    "$PYTHON_BIN" manage.py dbshell < "$sql_file"
}

echo "开始执行迁移"
"$PYTHON_BIN" manage.py migrate

run_sql "sql/fixtures/auth_group.sql"
run_sql "src/init_sql/mysql_slow_query_review.sql"

if [[ "$WITH_TEMPLATES" -eq 1 ]]; then
    run_sql "src/init_sql/rds_param_template.sql"
    run_sql "src/init_sql/goinception_param_template.sql"
fi

echo "初始化SQL导入完成"
