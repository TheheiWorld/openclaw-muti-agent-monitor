from datetime import datetime
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import verify_collector_api_key
from ..database import get_db
from ..models import Instance, Agent, Session, TokenUsageHourly

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


class SessionPayload(BaseModel):
    key: str = ""
    sessionId: str
    agentId: str = ""
    channel: str = ""
    displayName: str = ""
    status: str = ""
    inputTokens: int = 0
    outputTokens: int = 0
    totalTokens: int = 0
    contextTokens: int = 0
    estimatedCostUsd: float = 0.0
    modelProvider: str = ""
    model: str = ""
    startedAt: int | None = None
    endedAt: int | None = None
    updatedAt: int | None = None


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
    timestamp: int | None = None


def _ts_to_dt(ts: int | None) -> datetime | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts)


@router.post("/heartbeat")
async def receive_heartbeat(payload: HeartbeatPayload, db: AsyncSession = Depends(get_db)):
    now = datetime.now()

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
            continue  # 忽略没有 id 和 name 的脏数据
        db.add(Agent(
            instance_id=payload.instance_id,
            agent_id=ag.id,
            name=ag.name,
            identity_emoji=ag.identity.emoji,
            identity_theme=ag.identity.theme,
            updated_at=now,
        ))

    # --- upsert sessions + aggregate token usage ---
    current_hour = now.replace(minute=0, second=0, microsecond=0)
    token_agg: dict[str, dict] = {}  # key: f"{instance_id}:{agent_id}"

    for sess in payload.sessions:
        result = await db.execute(
            select(Session).where(
                Session.instance_id == payload.instance_id,
                Session.session_id == sess.sessionId,
            )
        )
        existing = result.scalar_one_or_none()

        # 计算本次 token 增量
        prev_input = 0
        prev_output = 0
        prev_total = 0
        if existing:
            prev_input = existing.input_tokens or 0
            prev_output = existing.output_tokens or 0
            prev_total = existing.total_tokens or 0

        delta_input = max(0, sess.inputTokens - prev_input)
        delta_output = max(0, sess.outputTokens - prev_output)
        delta_total = max(0, sess.totalTokens - prev_total)

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
                total_tokens=sess.totalTokens,
                context_tokens=sess.contextTokens,
                estimated_cost_usd=sess.estimatedCostUsd,
                model_provider=sess.modelProvider,
                model=sess.model,
                started_at=_ts_to_dt(sess.startedAt),
                ended_at=_ts_to_dt(sess.endedAt),
                updated_at=now,
            ))
            # 新 session 的全量 token 都算作增量
            delta_input = sess.inputTokens
            delta_output = sess.outputTokens
            delta_total = sess.totalTokens
        else:
            existing.session_key = sess.key
            existing.channel = sess.channel
            existing.display_name = sess.displayName
            existing.status = sess.status
            existing.input_tokens = sess.inputTokens
            existing.output_tokens = sess.outputTokens
            existing.total_tokens = sess.totalTokens
            existing.context_tokens = sess.contextTokens
            existing.estimated_cost_usd = sess.estimatedCostUsd
            existing.model_provider = sess.modelProvider
            existing.model = sess.model
            existing.started_at = _ts_to_dt(sess.startedAt)
            existing.ended_at = _ts_to_dt(sess.endedAt)
            existing.updated_at = now

        # 累积 token 增量
        if delta_input > 0 or delta_output > 0 or delta_total > 0:
            agg_key = f"{payload.instance_id}:{sess.agentId}"
            if agg_key not in token_agg:
                token_agg[agg_key] = {
                    "instance_id": payload.instance_id,
                    "agent_id": sess.agentId,
                    "input": 0, "output": 0, "total": 0, "count": 0,
                }
            token_agg[agg_key]["input"] += delta_input
            token_agg[agg_key]["output"] += delta_output
            token_agg[agg_key]["total"] += delta_total
            token_agg[agg_key]["count"] += 1

    # --- upsert token_usage_hourly ---
    for agg in token_agg.values():
        if agg["total"] == 0:
            continue
        result = await db.execute(
            select(TokenUsageHourly).where(
                TokenUsageHourly.instance_id == agg["instance_id"],
                TokenUsageHourly.agent_id == agg["agent_id"],
                TokenUsageHourly.hour == current_hour,
            )
        )
        usage = result.scalar_one_or_none()
        if usage is None:
            db.add(TokenUsageHourly(
                instance_id=agg["instance_id"],
                agent_id=agg["agent_id"],
                hour=current_hour,
                input_tokens_sum=agg["input"],
                output_tokens_sum=agg["output"],
                total_tokens_sum=agg["total"],
                session_count=agg["count"],
            ))
        else:
            usage.input_tokens_sum += agg["input"]
            usage.output_tokens_sum += agg["output"]
            usage.total_tokens_sum += agg["total"]
            usage.session_count += agg["count"]

    await db.commit()
    return {"ok": True}
