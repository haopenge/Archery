#!/usr/bin/env bash

set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

USERNAME=""
EMAIL=""
PASSWORD=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -u|--username)
            USERNAME="$2"
            shift 2
            ;;
        -e|--email)
            EMAIL="$2"
            shift 2
            ;;
        -p|--password)
            PASSWORD="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: sh create_admin_user.sh -u <username> [-e <email>] [-p <password>]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: sh create_admin_user.sh -u <username> [-e <email>] [-p <password>]"
            exit 1
            ;;
    esac
done

if [[ -z "$USERNAME" ]]; then
    echo "用户名不能为空，请使用 -u 或 --username 指定"
    exit 1
fi

if [[ -z "$PASSWORD" ]]; then
    read -rsp "请输入密码: " PASSWORD
    echo ""
    read -rsp "请再次输入密码: " PASSWORD_CONFIRM
    echo ""
    if [[ "$PASSWORD" != "$PASSWORD_CONFIRM" ]]; then
        echo "两次输入的密码不一致"
        exit 1
    fi
fi

if [[ -f "./.venv/bin/activate" ]]; then
    source ./.venv/bin/activate
    PYTHON_BIN="./.venv/bin/python3"
elif [[ -f "./venv/bin/activate" ]]; then
    source ./venv/bin/activate
    PYTHON_BIN="./venv/bin/python3"
elif [[ -f "/opt/venv4archery/bin/activate" ]]; then
    source /opt/venv4archery/bin/activate
    PYTHON_BIN="/opt/venv4archery/bin/python3"
else
    PYTHON_BIN="python3"
fi

if ! "$PYTHON_BIN" -c "import django" >/dev/null 2>&1; then
    echo "未找到可用的Django运行环境，请先执行 sh admin.sh init 或安装依赖"
    exit 1
fi

ARCHERY_SU_USERNAME="$USERNAME" \
ARCHERY_SU_EMAIL="$EMAIL" \
ARCHERY_SU_PASSWORD="$PASSWORD" \
"$PYTHON_BIN" manage.py shell <<'PY'
from django.contrib.auth import get_user_model
import os

username = os.environ["ARCHERY_SU_USERNAME"]
email = os.environ.get("ARCHERY_SU_EMAIL", "")
password = os.environ["ARCHERY_SU_PASSWORD"]

User = get_user_model()
user, created = User.objects.get_or_create(
    username=username,
    defaults={
        "email": email,
        "is_staff": True,
        "is_superuser": True,
        "is_active": True,
    },
)
if created:
    user.set_password(password)
    user.save(update_fields=["password"])
    print(f"创建管理员成功: {username}")
else:
    user.email = email
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    user.set_password(password)
    user.save(update_fields=["email", "is_staff", "is_superuser", "is_active", "password"])
    print(f"管理员已存在，已更新密码与权限: {username}")
PY
