from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Session

router = APIRouter(prefix="/api/sessions", tags=["sessions"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_sessions(
    instance_id: str | None = None,
    agent_id: str | None = None,
    channel: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    query = select(Session)
    if instance_id:
        query = query.where(Session.instance_id == instance_id)
    if agent_id:
        query = query.where(Session.agent_id == agent_id)
    if channel:
        query = query.where(Session.channel == channel)
    if status:
        query = query.where(Session.status == status)

    # total count
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Session.updated_at.desc()).offset(offset).limit(limit)
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

    return {"items": items, "total": total}
