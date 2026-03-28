from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..config import AGENT_DOCS_DIR
from ..database import get_db
from ..models import Agent, Session, Instance, TokenUsageDaily

AGENT_OFFLINE_MINUTES = 30

router = APIRouter(prefix="/api/agents", tags=["agents"], dependencies=[Depends(get_current_user)])


def _agent_status(updated_at) -> str:
    if not updated_at:
        return "offline"
    if datetime.now() - updated_at > timedelta(minutes=AGENT_OFFLINE_MINUTES):
        return "offline"
    return "active"


@router.get("")
async def list_agents(instance_id: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Agent)
    if instance_id:
        query = query.where(Agent.instance_id == instance_id)
    query = query.order_by(Agent.updated_at.desc())
    result = await db.execute(query)
    agents = result.scalars().all()

    items = []
    for ag in agents:
        # instance name
        inst_result = await db.execute(
            select(Instance.name).where(Instance.instance_id == ag.instance_id)
        )
        instance_name = inst_result.scalar() or ag.instance_id

        # session count from Session table, tokens from TokenUsageDaily
        sess_count = (await db.execute(
            select(func.count(Session.id)).where(
                Session.instance_id == ag.instance_id,
                Session.agent_id == ag.agent_id,
            )
        )).scalar() or 0

        token_total = (await db.execute(
            select(func.coalesce(func.sum(TokenUsageDaily.total_tokens_sum), 0)).where(
                TokenUsageDaily.instance_id == ag.instance_id,
                TokenUsageDaily.agent_id == ag.agent_id,
            )
        )).scalar() or 0

        items.append({
            "agent_id": ag.agent_id,
            "instance_id": ag.instance_id,
            "instance_name": instance_name,
            "name": ag.name,
            "identity_emoji": ag.identity_emoji,
            "identity_theme": ag.identity_theme,
            "status": _agent_status(ag.updated_at),
            "session_count": sess_count,
            "total_tokens": token_total,
            "updated_at": ag.updated_at.isoformat() if ag.updated_at else None,
        })

    items.sort(key=lambda x: x["total_tokens"], reverse=True)
    return {"items": items, "total": len(items)}


@router.get("/{agent_id}")
async def get_agent(agent_id: str, instance_id: str, db: AsyncSession = Depends(get_db)):
    """获取单个 Agent 详情"""
    result = await db.execute(
        select(Agent).where(Agent.instance_id == instance_id, Agent.agent_id == agent_id)
    )
    ag = result.scalar_one_or_none()
    if not ag:
        raise HTTPException(status_code=404, detail="Agent not found")

    inst_name = (await db.execute(
        select(Instance.name).where(Instance.instance_id == ag.instance_id)
    )).scalar() or ag.instance_id

    sess_count = (await db.execute(
        select(func.count(Session.id)).where(Session.instance_id == ag.instance_id, Session.agent_id == ag.agent_id)
    )).scalar() or 0

    token_stats = (await db.execute(
        select(
            func.coalesce(func.sum(TokenUsageDaily.total_tokens_sum), 0).label("total_tokens"),
            func.coalesce(func.sum(TokenUsageDaily.input_tokens_sum), 0).label("input_tokens"),
            func.coalesce(func.sum(TokenUsageDaily.output_tokens_sum), 0).label("output_tokens"),
            func.coalesce(func.sum(TokenUsageDaily.cache_read_tokens_sum), 0).label("cache_read_tokens"),
            func.coalesce(func.sum(TokenUsageDaily.cache_write_tokens_sum), 0).label("cache_write_tokens"),
        ).where(TokenUsageDaily.instance_id == ag.instance_id, TokenUsageDaily.agent_id == ag.agent_id)
    )).one()

    # cost still aggregated from sessions as it's updated in heartbeat
    cost_total = (await db.execute(
        select(func.coalesce(func.sum(Session.estimated_cost_usd), 0))
        .where(Session.instance_id == ag.instance_id, Session.agent_id == ag.agent_id)
    )).scalar() or 0

    return {
        "agent_id": ag.agent_id,
        "instance_id": ag.instance_id,
        "instance_name": inst_name,
        "name": ag.name,
        "identity_emoji": ag.identity_emoji,
        "identity_theme": ag.identity_theme,
        "workspace": ag.workspace,
        "agent_dir": ag.agent_dir,
        "model": ag.model,
        "status": _agent_status(ag.updated_at),
        "session_count": sess_count,
        "total_tokens": token_stats.total_tokens,
        "input_tokens": token_stats.input_tokens,
        "output_tokens": token_stats.output_tokens,
        "cache_read_tokens": token_stats.cache_read_tokens,
        "cache_write_tokens": token_stats.cache_write_tokens,
        "estimated_cost_usd": round(cost_total, 4),
        "updated_at": ag.updated_at.isoformat() if ag.updated_at else None,
    }


@router.get("/{agent_id}/sessions")
async def get_agent_sessions(
    agent_id: str,
    instance_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Session).where(Session.agent_id == agent_id)
    if instance_id:
        query = query.where(Session.instance_id == instance_id)
    query = query.order_by(Session.updated_at.desc()).limit(200)
    result = await db.execute(query)
    sessions = result.scalars().all()

    items = [{
        "session_id": s.session_id,
        "instance_id": s.instance_id,
        "agent_id": s.agent_id,
        "channel": s.channel,
        "display_name": s.display_name,
        "status": s.status,
        "input_tokens": s.input_tokens,
        "output_tokens": s.output_tokens,
        "total_tokens": s.total_tokens,
        "context_tokens": s.context_tokens,
        "estimated_cost_usd": s.estimated_cost_usd,
        "model_provider": s.model_provider,
        "model": s.model,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    } for s in sessions]

    return {"items": items, "total": len(items)}


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    instance_id: str,
    db: AsyncSession = Depends(get_db),
):
    """删除离线 Agent 及其关联的 sessions 和 token 统计"""
    result = await db.execute(
        select(Agent).where(Agent.instance_id == instance_id, Agent.agent_id == agent_id)
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if _agent_status(agent.updated_at) != "offline":
        raise HTTPException(status_code=400, detail="Only offline agents can be deleted")

    await db.execute(delete(TokenUsageHourly).where(
        TokenUsageHourly.instance_id == instance_id, TokenUsageHourly.agent_id == agent_id))
    await db.execute(delete(Session).where(
        Session.instance_id == instance_id, Session.agent_id == agent_id))
    await db.execute(delete(Agent).where(
        Agent.instance_id == instance_id, Agent.agent_id == agent_id))
    await db.commit()

    return {"ok": True}


@router.get("/{agent_id}/docs")
async def get_agent_docs(agent_id: str, instance_id: str):
    """获取 agent 的文档文件内容"""
    agent_dir = AGENT_DOCS_DIR / instance_id / agent_id
    files = {}
    if agent_dir.is_dir():
        for fpath in sorted(agent_dir.iterdir()):
            if fpath.suffix == ".md" and fpath.is_file():
                try:
                    files[fpath.name] = fpath.read_text(encoding="utf-8")
                except Exception:
                    pass
    return {"files": files}
