from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Agent, Session, Instance

router = APIRouter(prefix="/api/agents", tags=["agents"], dependencies=[Depends(get_current_user)])


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

        # session count + total tokens
        sess_stats = (await db.execute(
            select(
                func.count().label("session_count"),
                func.coalesce(func.sum(Session.total_tokens), 0).label("total_tokens"),
            ).where(
                Session.instance_id == ag.instance_id,
                Session.agent_id == ag.agent_id,
            )
        )).one()

        items.append({
            "agent_id": ag.agent_id,
            "instance_id": ag.instance_id,
            "instance_name": instance_name,
            "name": ag.name,
            "identity_emoji": ag.identity_emoji,
            "identity_theme": ag.identity_theme,
            "status": ag.status,
            "session_count": sess_stats.session_count,
            "total_tokens": sess_stats.total_tokens,
            "updated_at": ag.updated_at.isoformat() if ag.updated_at else None,
        })

    return {"items": items, "total": len(items)}


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
