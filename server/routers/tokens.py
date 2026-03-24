from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import TokenUsageHourly, Session, Instance, Agent

router = APIRouter(prefix="/api/tokens", tags=["tokens"], dependencies=[Depends(get_current_user)])


def _parse_range(range_str: str) -> datetime:
    now = datetime.now()
    if range_str == "7d":
        return now - timedelta(days=7)
    elif range_str == "30d":
        return now - timedelta(days=30)
    else:  # default 24h
        return now - timedelta(hours=24)


@router.get("/summary")
async def token_summary(db: AsyncSession = Depends(get_db)):
    """Token 用量总览: 总量 + 按实例分组 + 按 Agent 分组"""

    # 全局总量
    total_result = await db.execute(
        select(
            func.coalesce(func.sum(Session.input_tokens), 0).label("input"),
            func.coalesce(func.sum(Session.output_tokens), 0).label("output"),
            func.coalesce(func.sum(Session.total_tokens), 0).label("total"),
            func.coalesce(func.sum(Session.estimated_cost_usd), 0).label("cost"),
        )
    )
    total = total_result.one()

    # 按实例分组
    by_instance_result = await db.execute(
        select(
            Session.instance_id,
            func.sum(Session.total_tokens).label("total_tokens"),
            func.sum(Session.estimated_cost_usd).label("cost"),
        ).group_by(Session.instance_id).order_by(func.sum(Session.total_tokens).desc())
    )
    by_instance = []
    for row in by_instance_result.all():
        inst = (await db.execute(
            select(Instance.name).where(Instance.instance_id == row.instance_id)
        )).scalar() or row.instance_id
        by_instance.append({
            "instance_id": row.instance_id,
            "instance_name": inst,
            "total_tokens": row.total_tokens or 0,
            "estimated_cost_usd": round(row.cost or 0, 4),
        })

    # 按 Agent 分组 (top 20)
    by_agent_result = await db.execute(
        select(
            Session.agent_id,
            Session.instance_id,
            func.sum(Session.total_tokens).label("total_tokens"),
            func.sum(Session.estimated_cost_usd).label("cost"),
        ).group_by(Session.instance_id, Session.agent_id)
        .order_by(func.sum(Session.total_tokens).desc())
        .limit(20)
    )
    by_agent = []
    for row in by_agent_result.all():
        agent_name = (await db.execute(
            select(Agent.name).where(Agent.instance_id == row.instance_id, Agent.agent_id == row.agent_id)
        )).scalar() or row.agent_id
        by_agent.append({
            "agent_id": row.agent_id,
            "agent_name": agent_name,
            "instance_id": row.instance_id,
            "total_tokens": row.total_tokens or 0,
            "estimated_cost_usd": round(row.cost or 0, 4),
        })

    return {
        "total_input_tokens": total.input,
        "total_output_tokens": total.output,
        "total_tokens": total.total,
        "total_cost_usd": round(total.cost, 4),
        "by_instance": by_instance,
        "by_agent": by_agent,
    }


@router.get("/trend")
async def token_trend(
    range: str = Query("24h", pattern="^(24h|7d|30d)$"),
    instance_id: str | None = None,
    agent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Token 用量趋势 (按小时聚合)"""
    since = _parse_range(range)

    query = select(
        TokenUsageHourly.hour,
        func.sum(TokenUsageHourly.input_tokens_sum).label("input"),
        func.sum(TokenUsageHourly.output_tokens_sum).label("output"),
        func.sum(TokenUsageHourly.total_tokens_sum).label("total"),
        func.sum(TokenUsageHourly.session_count).label("sessions"),
    ).where(TokenUsageHourly.hour >= since)

    if instance_id:
        query = query.where(TokenUsageHourly.instance_id == instance_id)
    if agent_id:
        query = query.where(TokenUsageHourly.agent_id == agent_id)

    query = query.group_by(TokenUsageHourly.hour).order_by(TokenUsageHourly.hour)
    result = await db.execute(query)

    points = [{
        "hour": row.hour.isoformat(),
        "input_tokens": row.input or 0,
        "output_tokens": row.output or 0,
        "total_tokens": row.total or 0,
        "session_count": row.sessions or 0,
    } for row in result.all()]

    return {"range": range, "points": points}
