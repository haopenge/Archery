#!/bin/bash

# 激活虚拟环境
source .venv/bin/activate

# 启动服务
supervisord -c supervisord.conf
