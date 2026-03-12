#!/bin/bash

# 激活虚拟环境
source .venv/bin/activate

# 收集所有的静态文件到 STATIC_ROOT
python manage.py collectstatic -v0 --noinput

# 启动服务
supervisord -c supervisord.conf

