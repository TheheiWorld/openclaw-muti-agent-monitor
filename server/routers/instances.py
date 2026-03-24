from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Instance, Agent, Session, TokenUsageHourly

router = APIRouter(prefix="/api/instances", tags=["instances"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_instances(status: str | None = None, db: AsyncSession = Depends(get_db)):
    query = select(Instance)
    if status:
        query = query.where(Instance.status == status)
    query = query.order_by(Instance.updated_at.desc())
    result = await db.execute(query)
    instances = result.scalars().all()

    items = []
    for inst in instances:
        # agent count
        agent_count = (await db.execute(
            select(func.count()).where(Agent.instance_id == inst.instance_id)
        )).scalar() or 0

        # total tokens
        total_tokens = (await db.execute(
            select(func.coalesce(func.sum(Session.total_tokens), 0)).where(
                Session.instance_id == inst.instance_id
            )
        )).scalar() or 0

        items.append({
            "id": inst.id,
            "instance_id": inst.instance_id,
            "name": inst.name,
            "hostname": inst.hostname or "",
            "host": inst.host,
            "port": inst.port,
            "status": inst.status,
            "version": inst.version,
            "last_heartbeat": inst.last_heartbeat.isoformat() if inst.last_heartbeat else None,
            "agent_count": agent_count,
            "total_tokens": total_tokens,
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
        })

    return {"items": items, "total": len(items)}


@router.get("/{instance_id}")
async def get_instance(instance_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Instance).where(Instance.instance_id == instance_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")

    # agents
    agents_result = await db.execute(
        select(Agent).where(Agent.instance_id == instance_id).order_by(Agent.updated_at.desc())
    )
    agents = agents_result.scalars().all()

    agent_items = []
    for ag in agents:
        sess_stats = (await db.execute(
            select(
                func.count().label("session_count"),
                func.coalesce(func.sum(Session.total_tokens), 0).label("total_tokens"),
            ).where(
                Session.instance_id == instance_id,
                Session.agent_id == ag.agent_id,
            )
        )).one()

        agent_items.append({
            "agent_id": ag.agent_id,
            "name": ag.name,
            "identity_emoji": ag.identity_emoji,
            "identity_theme": ag.identity_theme,
            "status": ag.status,
            "session_count": sess_stats.session_count,
            "total_tokens": sess_stats.total_tokens,
            "updated_at": ag.updated_at.isoformat() if ag.updated_at else None,
        })

    # sessions
    sessions_result = await db.execute(
        select(Session).where(Session.instance_id == instance_id).order_by(Session.updated_at.desc()).limit(100)
    )
    sessions = sessions_result.scalars().all()

    session_items = [{
        "session_id": s.session_id,
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

    return {
        "instance_id": inst.instance_id,
        "name": inst.name,
        "hostname": inst.hostname or "",
        "host": inst.host,
        "port": inst.port,
        "status": inst.status,
        "version": inst.version,
        "last_heartbeat": inst.last_heartbeat.isoformat() if inst.last_heartbeat else None,
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
        "agents": agent_items,
        "sessions": session_items,
    }


@router.delete("/{instance_id}")
async def delete_instance(instance_id: str, db: AsyncSession = Depends(get_db)):
    """删除离线实例及其关联数据（仅允许删除 offline 状态的实例）"""
    result = await db.execute(
        select(Instance).where(Instance.instance_id == instance_id)
    )
    inst = result.scalar_one_or_none()
    if not inst:
        raise HTTPException(status_code=404, detail="Instance not found")
    if inst.status != "offline":
        raise HTTPException(status_code=400, detail="Only offline instances can be deleted")

    # 删除关联数据
    await db.execute(delete(TokenUsageHourly).where(TokenUsageHourly.instance_id == instance_id))
    await db.execute(delete(Session).where(Session.instance_id == instance_id))
    await db.execute(delete(Agent).where(Agent.instance_id == instance_id))
    await db.execute(delete(Instance).where(Instance.instance_id == instance_id))
    await db.commit()

    return {"ok": True}
