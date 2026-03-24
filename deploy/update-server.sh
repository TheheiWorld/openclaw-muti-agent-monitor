#!/usr/bin/env bash
#
# OpenClaw Monitor Server 更新部署脚本
#
# 用法:
#   sudo bash deploy/update-server.sh                # 从 git 拉取最新代码并重新部署
#   sudo bash deploy/update-server.sh /path/to/repo  # 指定源码目录
#

set -euo pipefail

DEPLOY_DIR="/opt/openclaw-monitor"
VENV_DIR="${DEPLOY_DIR}/venv"
SERVICE_NAME="openclaw-monitor"
USER="openclaw-monitor"
SOURCE_DIR="${1:-$(cd "$(dirname "$0")/.." && pwd)}"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# 检查 root 权限
[[ $EUID -eq 0 ]] || error "请使用 sudo 运行此脚本"

# 检查源码目录
[[ -d "${SOURCE_DIR}/server" ]] || error "源码目录不存在或不完整: ${SOURCE_DIR}/server"

info "源码目录: ${SOURCE_DIR}"
info "部署目录: ${DEPLOY_DIR}"

# 1. 拉取最新代码（如果是 git 仓库）
if [[ -d "${SOURCE_DIR}/.git" ]]; then
    info "拉取最新代码..."
    cd "${SOURCE_DIR}"
    sudo -u "${USER}" git pull 2>/dev/null || {
        # 如果 openclaw-monitor 用户无权限，用当前用户拉取
        git pull
    }
fi

# 2. 同步文件到部署目录
info "同步 server 代码..."
rsync -a --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.db' \
    --exclude='.env' \
    "${SOURCE_DIR}/server/" "${DEPLOY_DIR}/server/"

info "同步 collector 代码..."
rsync -a --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.instance_id' \
    "${SOURCE_DIR}/collector/" "${DEPLOY_DIR}/collector/"
# 保留采集器本地配置
if [[ ! -f "${DEPLOY_DIR}/collector/config.yaml" ]]; then
    cp "${SOURCE_DIR}/collector/config.yaml" "${DEPLOY_DIR}/collector/config.yaml"
fi

info "同步 deploy 文件..."
rsync -a "${SOURCE_DIR}/deploy/" "${DEPLOY_DIR}/deploy/"

# 2.5 构建前端
if [[ -d "${SOURCE_DIR}/web" ]]; then
    if command -v node &>/dev/null && [[ -f "${SOURCE_DIR}/web/package.json" ]]; then
        info "构建前端..."
        cd "${SOURCE_DIR}/web"
        npm install --silent 2>/dev/null
        npm run build
        info "同步前端产物..."
        mkdir -p "${DEPLOY_DIR}/web/dist"
        rsync -a --delete "${SOURCE_DIR}/web/dist/" "${DEPLOY_DIR}/web/dist/"
    else
        warn "未找到 Node.js 或 package.json，跳过前端构建"
        # 如果源码中已有 dist，直接同步
        if [[ -d "${SOURCE_DIR}/web/dist" ]]; then
            mkdir -p "${DEPLOY_DIR}/web/dist"
            rsync -a --delete "${SOURCE_DIR}/web/dist/" "${DEPLOY_DIR}/web/dist/"
        fi
    fi
fi

# 3. 修复文件权限
chown -R "${USER}:${USER}" "${DEPLOY_DIR}/server" "${DEPLOY_DIR}/collector" "${DEPLOY_DIR}/deploy"
[[ -d "${DEPLOY_DIR}/web" ]] && chown -R "${USER}:${USER}" "${DEPLOY_DIR}/web"

# 4. 更新 Python 依赖
info "更新 Python 依赖..."
sudo -u "${USER}" "${VENV_DIR}/bin/pip" install -q -r "${DEPLOY_DIR}/server/requirements.txt"
if [[ -f "${DEPLOY_DIR}/collector/requirements.txt" ]]; then
    sudo -u "${USER}" "${VENV_DIR}/bin/pip" install -q -r "${DEPLOY_DIR}/collector/requirements.txt"
fi

# 5. 执行数据库迁移
info "执行数据库迁移..."
cd "${DEPLOY_DIR}"
sudo -u "${USER}" bash -c 'set -a; source .env 2>/dev/null; set +a; '"${VENV_DIR}"'/bin/python -m server.init_db'

# 6. 更新 systemd 服务文件（如有变化）
if ! diff -q "${DEPLOY_DIR}/deploy/openclaw-monitor.service" /etc/systemd/system/openclaw-monitor.service &>/dev/null 2>&1; then
    info "更新 systemd 服务文件..."
    cp "${DEPLOY_DIR}/deploy/openclaw-monitor.service" /etc/systemd/system/
    cp "${DEPLOY_DIR}/deploy/openclaw-collector.service" /etc/systemd/system/
    systemctl daemon-reload
fi

# 7. 重启服务
info "重启 ${SERVICE_NAME} 服务..."
systemctl restart "${SERVICE_NAME}"

# 等待服务启动
sleep 2

# 8. 检查服务状态
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    info "服务重启成功"
    systemctl status "${SERVICE_NAME}" --no-pager -l
else
    error "服务启动失败，请检查日志: journalctl -u ${SERVICE_NAME} -n 50"
fi

echo ""
info "部署完成!"
