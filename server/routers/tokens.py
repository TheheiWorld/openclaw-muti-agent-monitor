from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import TokenUsageDaily, Session, Instance, Agent

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
    """Token 用量总览: 全部由 TokenUsageDaily 提供"""

    # 全局总量 (Tokens)
    tokens_result = await db.execute(
        select(
            func.coalesce(func.sum(TokenUsageDaily.input_tokens_sum), 0).label("input"),
            func.coalesce(func.sum(TokenUsageDaily.output_tokens_sum), 0).label("output"),
            func.coalesce(func.sum(TokenUsageDaily.total_tokens_sum), 0).label("total"),
        )
    )
    tokens = tokens_result.one()

    # 全局费用 (Session)
    cost_total = (await db.execute(
        select(func.coalesce(func.sum(Session.estimated_cost_usd), 0))
    )).scalar() or 0

    # 按实例分组 (Daily)
    by_instance_result = await db.execute(
        select(
            TokenUsageDaily.instance_id,
            func.sum(TokenUsageDaily.total_tokens_sum).label("total_tokens"),
        ).group_by(TokenUsageDaily.instance_id).order_by(func.sum(TokenUsageDaily.total_tokens_sum).desc())
    )
    by_instance = []
    for row in by_instance_result.all():
        inst = (await db.execute(
            select(Instance.name).where(Instance.instance_id == row.instance_id)
        )).scalar() or row.instance_id
        inst_cost = (await db.execute(
            select(func.coalesce(func.sum(Session.estimated_cost_usd), 0)).where(Session.instance_id == row.instance_id)
        )).scalar() or 0
        by_instance.append({
            "instance_id": row.instance_id,
            "instance_name": inst,
            "total_tokens": row.total_tokens or 0,
            "estimated_cost_usd": round(inst_cost, 4),
        })

    # 按 Agent 分组 (Daily)
    by_agent_result = await db.execute(
        select(
            TokenUsageDaily.agent_id,
            TokenUsageDaily.instance_id,
            func.sum(TokenUsageDaily.total_tokens_sum).label("total_tokens"),
        ).group_by(TokenUsageDaily.instance_id, TokenUsageDaily.agent_id)
        .order_by(func.sum(TokenUsageDaily.total_tokens_sum).desc())
        .limit(20)
    )
    by_agent = []
    for row in by_agent_result.all():
        agent_name = (await db.execute(
            select(Agent.name).where(Agent.instance_id == row.instance_id, Agent.agent_id == row.agent_id)
        )).scalar() or row.agent_id
        agent_cost = (await db.execute(
            select(func.coalesce(func.sum(Session.estimated_cost_usd), 0))
            .where(Session.instance_id == row.instance_id, Session.agent_id == row.agent_id)
        )).scalar() or 0
        by_agent.append({
            "agent_id": row.agent_id,
            "agent_name": agent_name,
            "instance_id": row.instance_id,
            "total_tokens": row.total_tokens or 0,
            "estimated_cost_usd": round(agent_cost, 4),
        })

    return {
        "total_input_tokens": tokens.input,
        "total_output_tokens": tokens.output,
        "total_tokens": tokens.total,
        "total_cost_usd": round(cost_total, 4),
        "by_instance": by_instance,
        "by_agent": by_agent,
    }


@router.get("/trend")
async def token_trend(
    range: str = Query("7d", pattern="^(24h|7d|30d)$"),
    instance_id: str | None = None,
    agent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Token 用量趋势 (按天聚合)"""
    since = _parse_range(range)

    query = select(
        TokenUsageDaily.date,
        func.sum(TokenUsageDaily.input_tokens_sum).label("input"),
        func.sum(TokenUsageDaily.output_tokens_sum).label("output"),
        func.sum(TokenUsageDaily.total_tokens_sum).label("total"),
    ).where(TokenUsageDaily.date >= since)

    if instance_id:
        query = query.where(TokenUsageDaily.instance_id == instance_id)
    if agent_id:
        query = query.where(TokenUsageDaily.agent_id == agent_id)

    query = query.group_by(TokenUsageDaily.date).order_by(TokenUsageDaily.date)
    result = await db.execute(query)

    points = [{
        "date": row.date.strftime("%Y-%m-%d"),
        "input_tokens": row.input or 0,
        "output_tokens": row.output or 0,
        "total_tokens": row.total or 0,
    } for row in result.all()]

    return {"range": range, "points": points}
