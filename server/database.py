import logging
import secrets

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import event, text, select

from .config import DATABASE_URL
from .models import Base, User

logger = logging.getLogger("server")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # 简易迁移: 给已有表补加新列 (SQLite create_all 不会自动添加)
        await _migrate_add_columns(conn)
    # 确保默认用户存在
    await _ensure_default_user()


async def _migrate_add_columns(conn):
    """检查并添加缺失的列"""
    migrations = [
        ("instances", "hostname", "VARCHAR(256) DEFAULT ''"),
    ]
    for table, column, col_def in migrations:
        try:
            await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}"))
        except Exception:
            # 列已存在，忽略
            pass


async def _ensure_default_user():
    """首次启动时创建默认用户 monitor 并打印随机密码"""
    from passlib.hash import bcrypt

    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == "monitor"))
        if result.scalar_one_or_none() is not None:
            logger.info("Default user 'monitor' already exists, skipping creation.")
            print("Default user 'monitor' already exists.")
            return

        password = secrets.token_urlsafe(12)
        hashed = bcrypt.hash(password)
        session.add(User(username="monitor", hashed_password=hashed))
        await session.commit()

        _print_credentials("monitor", password)
        logger.info("Default user 'monitor' created.")


async def reset_default_password():
    """重置 monitor 用户密码"""
    from passlib.hash import bcrypt

    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == "monitor"))
        user = result.scalar_one_or_none()
        if user is None:
            print("User 'monitor' not found, creating...")
            await _ensure_default_user()
            return

        password = secrets.token_urlsafe(12)
        user.hashed_password = bcrypt.hash(password)
        await session.commit()

        _print_credentials("monitor", password)
        logger.info("Password for 'monitor' has been reset.")


def _print_credentials(username: str, password: str):
    print("\n" + "=" * 60)
    print("  OpenClaw Monitor - 初始化完成")
    print()
    print(f"  用户名: {username}")
    print(f"  密码:   {password}")
    print()
    print("  请登录后尽快修改密码。")
    print("=" * 60 + "\n")


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
