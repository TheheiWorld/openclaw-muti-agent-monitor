#!/usr/bin/env python3
"""
数据库初始化脚本
用法: python -m server.init_db
功能: 创建所有表并生成默认用户 monitor（密码打印到控制台）
"""
import asyncio
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.database import init_db


async def main():
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully.")


if __name__ == "__main__":
    asyncio.run(main())
