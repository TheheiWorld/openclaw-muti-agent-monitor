import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Union

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import verify_collector_api_key
from ..config import AGENT_DOCS_DIR
from ..database import get_db
from ..models import Instance, Agent, Session, TokenUsageHourly, TokenUsageDaily

logger = logging.getLogger("server")

router = APIRouter(
    prefix="/api/collector",
    tags=["collector"],
    dependencies=[Depends(verify_collector_api_key)],
)


class AgentIdentity(BaseModel):
    emoji: str = ""
    theme: str = ""


class AgentPayload(BaseModel):
    id: str
    name: str = ""
    identity: AgentIdentity = AgentIdentity()
    workspace: str = ""
    agentDir: str = ""
    model: str = ""


class SessionPayload(BaseModel):
    key: str = ""
    sessionId: str
    agentId: str = ""
    channel: str = ""
    displayName: str = ""
    status: str = ""
    inputTokens: int = 0
    outputTokens: int = 0
    cacheReadTokens: int = 0
    cacheWriteTokens: int = 0
    totalTokens: int = 0
    contextTokens: int = 0
    estimatedCostUsd: float = 0.0
    modelProvider: str = ""
    model: str = ""
    startedAt: Union[int, str, None] = None
    endedAt: Union[int, str, None] = None
    updatedAt: Union[int, str, None] = None


class HourlyUsageItem(BaseModel):
    agent_id: str
    hour: str  # YYYY-MM-DD HH:00:00
    input: int = 0
    output: int = 0
    total: int = 0


class HealthPayload(BaseModel):
    live: bool = False
    ready: bool = False


class HeartbeatPayload(BaseModel):
    instance_id: str
    instance_name: str
    hostname: str = ""
    host: str
    port: int = 18789
    version: str = ""
    health: HealthPayload = HealthPayload()
    agents: list[AgentPayload] = []
    sessions: list[SessionPayload] = []
    hourly_usage: list[HourlyUsageItem] = []
    timestamp: int | None = None


def _ts_to_dt(ts: Union[int, str, None]) -> datetime | None:
    if ts is None:
        return None
    if isinstance(ts, str):
        try:
            # 处理 ISO 格式
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            if ts.isdigit():
                ts = int(ts)
            else:
                return None

    if isinstance(ts, int):
        # 13位以上认为是毫秒
        if ts > 10**11:
            return datetime.fromtimestamp(ts / 1000.0)
        return datetime.fromtimestamp(ts)
    return None


@router.post("/heartbeat")
async def receive_heartbeat(payload: HeartbeatPayload, db: AsyncSession = Depends(get_db)):
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # --- upsert instance ---
    result = await db.execute(
        select(Instance).where(Instance.instance_id == payload.instance_id)
    )
    instance = result.scalar_one_or_none()

    if payload.health.live and payload.health.ready:
        status = "online"
    elif payload.health.live:
        status = "unhealthy"
    else:
        status = "offline"

    if instance is None:
        instance = Instance(
            instance_id=payload.instance_id,
            name=payload.instance_name,
            hostname=payload.hostname,
            host=payload.host,
            port=payload.port,
            version=payload.version,
            status=status,
            last_heartbeat=now,
            created_at=now,
            updated_at=now,
        )
        db.add(instance)
    else:
        instance.name = payload.instance_name
        instance.hostname = payload.hostname
        instance.host = payload.host
        instance.port = payload.port
        instance.version = payload.version
        instance.status = status
        instance.last_heartbeat = now
        instance.updated_at = now

    # --- 全量覆盖 agents ---
    await db.execute(delete(Agent).where(Agent.instance_id == payload.instance_id))
    for ag in payload.agents:
        if not ag.id and not ag.name:
            continue
        db.add(Agent(
            instance_id=payload.instance_id,
            agent_id=ag.id,
            name=ag.name,
            identity_emoji=ag.identity.emoji,
            identity_theme=ag.identity.theme,
            workspace=ag.workspace,
            agent_dir=ag.agentDir,
            model=ag.model,
            updated_at=now,
        ))

    # --- upsert sessions ---
    for sess in payload.sessions:
        result = await db.execute(
            select(Session).where(
                Session.instance_id == payload.instance_id,
                Session.session_id == sess.sessionId,
            )
        )
        existing = result.scalar_one_or_none()

        if existing is None:
            db.add(Session(
                instance_id=payload.instance_id,
                agent_id=sess.agentId,
                session_id=sess.sessionId,
                session_key=sess.key,
                channel=sess.channel,
                display_name=sess.displayName,
                status=sess.status,
                input_tokens=sess.inputTokens,
                output_tokens=sess.outputTokens,
                cache_read_tokens=sess.cacheReadTokens,
                cache_write_tokens=sess.cacheWriteTokens,
                total_tokens=sess.totalTokens,
                context_tokens=sess.contextTokens,
                estimated_cost_usd=sess.estimatedCostUsd,
                model_provider=sess.modelProvider,
                model=sess.model,
                started_at=_ts_to_dt(sess.startedAt),
                ended_at=_ts_to_dt(sess.endedAt),
                updated_at=_ts_to_dt(sess.updatedAt) or now,
            ))
        else:
            existing.session_key = sess.key
            existing.channel = sess.channel
            existing.display_name = sess.displayName
            existing.status = sess.status
            existing.input_tokens = sess.inputTokens
            existing.output_tokens = sess.outputTokens
            existing.cache_read_tokens = sess.cacheReadTokens
            existing.cache_write_tokens = sess.cacheWriteTokens
            existing.total_tokens = sess.totalTokens
            existing.context_tokens = sess.contextTokens
            existing.estimated_cost_usd = sess.estimatedCostUsd
            existing.model_provider = sess.modelProvider
            existing.model = sess.model
            existing.started_at = _ts_to_dt(sess.startedAt)
            existing.ended_at = _ts_to_dt(sess.endedAt)
            existing.updated_at = _ts_to_dt(sess.updatedAt) or now

    # --- 处理 TokenUsageHourly (同步覆盖逻辑) ---
    if payload.hourly_usage:
        # 1. 识别涉及到的 agent
        affected_agents = set(item.agent_id for item in payload.hourly_usage)
        
        # 2. 删除这些 agent 今天的旧数据 (只保留当天)
        for aid in affected_agents:
            await db.execute(
                delete(TokenUsageHourly).where(
                    TokenUsageHourly.instance_id == payload.instance_id,
                    TokenUsageHourly.agent_id == aid,
                    TokenUsageHourly.hour >= today_start
                )
            )
        
        # 3. 插入新数据
        for item in payload.hourly_usage:
            try:
                hour_dt = datetime.strptime(item.hour, "%Y-%m-%d %H:00:00")
            except ValueError:
                continue
            
            db.add(TokenUsageHourly(
                instance_id=payload.instance_id,
                agent_id=item.agent_id,
                hour=hour_dt,
                input_tokens_sum=item.input,
                output_tokens_sum=item.output,
                total_tokens_sum=item.total,
                session_count=0,
            ))

    await db.commit()
    return {"ok": True}


class DailyUsageItem(BaseModel):
    agent_id: str
    date: str  # YYYY-MM-DD
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total: int = 0


class DailyUsagePayload(BaseModel):
    instance_id: str
    items: list[DailyUsageItem]


@router.post("/daily-usage")
async def receive_daily_usage(payload: DailyUsagePayload, db: AsyncSession = Depends(get_db)):
    """接收 collector 上报的每日 Agent Token 消耗统计"""
    for item in payload.items:
        try:
            date_dt = datetime.strptime(item.date, "%Y-%m-%d")
        except ValueError:
            continue

        result = await db.execute(
            select(TokenUsageDaily).where(
                TokenUsageDaily.instance_id == payload.instance_id,
                TokenUsageDaily.agent_id == item.agent_id,
                TokenUsageDaily.date == date_dt,
            )
        )
        usage = result.scalar_one_or_none()

        if usage is None:
            db.add(TokenUsageDaily(
                instance_id=payload.instance_id,
                agent_id=item.agent_id,
                date=date_dt,
                input_tokens_sum=item.input,
                output_tokens_sum=item.output,
                cache_read_tokens_sum=item.cache_read,
                cache_write_tokens_sum=item.cache_write,
                total_tokens_sum=item.total,
            ))
        else:
            usage.input_tokens_sum = item.input
            usage.output_tokens_sum = item.output
            usage.cache_read_tokens_sum = item.cache_read
            usage.cache_write_tokens_sum = item.cache_write
            usage.total_tokens_sum = item.total

    await db.commit()
    logger.info(f"Daily usage received: {len(payload.items)} items from {payload.instance_id}")
    return {"ok": True}


# ---------- Agent 文档同步 ----------

SAFE_NAME_RE = re.compile(r"^[a-zA-Z0-9._-]+$")


class AgentDocsItem(BaseModel):
    agentId: str
    files: dict[str, str]  # filename -> content


class AgentDocsPayload(BaseModel):
    instance_id: str
    agents: list[AgentDocsItem]


@router.post("/agent-docs")
async def receive_agent_docs(payload: AgentDocsPayload):
    """接收 collector 上报的 agent 文档文件，存储到文件系统"""
    allowed_files = {"SOUL.md", "AGENTS.md", "IDENTITY.md", "USER.md", "TOOLS.md"}
    count = 0

    for ag in payload.agents:
        if not ag.agentId or not SAFE_NAME_RE.match(ag.agentId):
            continue
        if not SAFE_NAME_RE.match(payload.instance_id):
            continue

        agent_dir = AGENT_DOCS_DIR / payload.instance_id / ag.agentId
        agent_dir.mkdir(parents=True, exist_ok=True)

        for fname, content in ag.files.items():
            if fname not in allowed_files:
                continue
            fpath = agent_dir / fname
            fpath.write_text(content, encoding="utf-8")
            count += 1

    logger.info(f"Agent docs received: {len(payload.agents)} agents, {count} files")
    return {"ok": True}
