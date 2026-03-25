import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'monitor.db'}")

# 实例离线判定: 超过此秒数未收到心跳则标记 offline
HEARTBEAT_TIMEOUT_SECONDS = int(os.getenv("HEARTBEAT_TIMEOUT", "180"))

# 状态检测间隔 (秒)
STATUS_CHECK_INTERVAL = int(os.getenv("STATUS_CHECK_INTERVAL", "30"))

# 服务端口
SERVER_PORT = int(os.getenv("SERVER_PORT", "9200"))

# JWT 认证配置
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "24"))

# Collector API Key 认证
COLLECTOR_API_KEY = os.getenv("COLLECTOR_API_KEY", "123456")

# Agent 文档存储目录
AGENT_DOCS_DIR = Path(os.getenv("AGENT_DOCS_DIR", str(BASE_DIR / "data" / "agent-docs")))
