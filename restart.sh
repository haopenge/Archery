#!/bin/bash

# 激活虚拟环境
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
