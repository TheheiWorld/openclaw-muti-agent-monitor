import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update

from .config import HEARTBEAT_TIMEOUT_SECONDS, STATUS_CHECK_INTERVAL, SERVER_PORT
from .database import init_db, async_session
from .models import Instance
from .routers import auth, collector, instances, agents, sessions, tokens, dashboard


async def check_instance_status():
    """后台任务: 定期检查实例心跳，标记超时实例为 offline"""
    while True:
        await asyncio.sleep(STATUS_CHECK_INTERVAL)
        try:
            cutoff = datetime.now() - timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS)
            async with async_session() as db:
                await db.execute(
                    update(Instance)
                    .where(Instance.last_heartbeat < cutoff, Instance.status != "offline")
                    .values(status="offline", updated_at=datetime.now())
                )
                await db.commit()
        except Exception as e:
            print(f"[status-checker] error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(check_instance_status())
    yield
    task.cancel()


app = FastAPI(
    title="OpenClaw Monitor",
    description="多实例多 Agent 监控系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(collector.router)
app.include_router(dashboard.router)
app.include_router(instances.router)
app.include_router(agents.router)
app.include_router(sessions.router)
app.include_router(tokens.router)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server.main:app", host="0.0.0.0", port=SERVER_PORT, reload=True)
