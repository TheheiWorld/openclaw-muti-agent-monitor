#!/bin/bash

# OpenClaw Collector 一键部署/更新脚本
# 运行环境: Linux (Systemd)

set -e

# 配置变量
INSTALL_DIR="/opt/openclaw-collector"
SERVICE_NAME="openclaw-collector"
PYTHON_BIN="python3"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo -e "${GREEN}>>> OpenClaw Collector 部署/更新工具${NC}"

# 1. 检查权限
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}请使用 sudo 运行此脚本${NC}"
  exit 1
fi

# 2. 准备目录
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "创建安装目录: $INSTALL_DIR"
    mkdir -p "$INSTALL_DIR"
fi

# 3. 同步文件 (假设脚本在项目根目录运行)
echo "同步代码文件..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cp "$PROJECT_ROOT/collector/collector.py" "$INSTALL_DIR/"
cp "$PROJECT_ROOT/collector/requirements.txt" "$INSTALL_DIR/"

# 4. 初始化配置 (如果不存在)
CONFIG_FILE="$INSTALL_DIR/config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}>>> 首次安装，请配置基本信息:${NC}"
    read -p "监控服务端地址 (默认 http://127.0.0.1:9200): " SERVER_URL
    SERVER_URL=${SERVER_URL:-"http://127.0.0.1:9200"}
    
    read -p "Collector API Key: " API_KEY
    
    read -p "当前实例名称 (例如 prod-01): " INST_NAME
    
    cat > "$CONFIG_FILE" <<EOF
# OpenClaw Monitor Collector 配置
server_url: "$SERVER_URL"
api_key: "$API_KEY"
instance_name: "$INST_NAME"

# 采集间隔 (秒)
heartbeat_interval: 60
agents_interval: 120
sessions_interval: 60
doc_sync_interval: 3600

# OpenClaw 配置
openclaw_host: "127.0.0.1"
openclaw_port: 18789
openclaw_bin: "openclaw"
openclaw_home: ""
EOF
    echo "配置文件已生成: $CONFIG_FILE"
fi

# 5. 设置虚拟环境
echo "设置 Python 虚拟环境..."
cd "$INSTALL_DIR"
if [ ! -d "venv" ]; then
    $PYTHON_BIN -m venv venv
fi
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 6. 配置 Systemd 服务
echo "配置 Systemd 服务..."
cat > /etc/systemd/system/$SERVICE_NAME.service <<EOF
[Unit]
Description=OpenClaw Multi-Agent Monitor Collector
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/collector.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 7. 启动服务
echo "重载并启动服务..."
systemctl daemon-reload
systemctl enable $SERVICE_NAME
systemctl restart $SERVICE_NAME

echo -e "${GREEN}>>> 部署成功！${NC}"
echo -e "服务状态: ${GREEN}$(systemctl is-active $SERVICE_NAME)${NC}"
echo -e "你可以通过以下命令查看日志:"
echo -e "  journalctl -u $SERVICE_NAME -f"
