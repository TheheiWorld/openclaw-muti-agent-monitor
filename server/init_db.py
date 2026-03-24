#!/usr/bin/env python3
"""
数据库初始化脚本

用法:
  python -m server.init_db                 # 初始化数据库 + 创建默认用户
  python -m server.init_db --reset-password # 重置 monitor 用户密码
"""
import argparse
import asyncio
import sys
from pathlib import Path

# 将项目根目录加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.database import init_db, reset_default_password


async def main():
    parser = argparse.ArgumentParser(description="OpenClaw Monitor 数据库初始化")
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="重置 monitor 用户密码",
    )
    args = parser.parse_args()

    print("Initializing database...")
    await init_db()
    print("Database initialized successfully.\n")

    if args.reset_password:
        await reset_default_password()


if __name__ == "__main__":
    asyncio.run(main())
