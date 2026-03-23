#!/usr/bin/env python3
"""启动 OpenClaw Monitor 后端服务"""
import sys
from pathlib import Path

# 将项目根目录加入 sys.path，使 server 包的相对导入正常工作
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn
from server.config import SERVER_PORT

if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=SERVER_PORT, reload=True)
