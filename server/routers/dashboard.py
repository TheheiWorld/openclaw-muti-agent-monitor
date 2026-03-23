from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Instance, Agent, Session, TokenUsageHourly

router = APIRouter(prefix="/api", tags=["dashboard"], dependencies=[Depends(get_current_user)])


@router.get("/dashboard")
async def dashboard(db: AsyncSession = Depends(get_db)):
    """Dashboard 汇总数据"""

    # 实例统计
    total_instances = (await db.execute(select(func.count()).select_from(Instance))).scalar() or 0
    online_instances = (await db.execute(
        select(func.count()).where(Instance.status == "online")
    )).scalar() or 0
    offline_instances = (await db.execute(
        select(func.count()).where(Instance.status == "offline")
    )).scalar() or 0
    unhealthy_instances = (await db.execute(
        select(func.count()).where(Instance.status == "unhealthy")
    )).scalar() or 0

    # Agent 统计
    total_agents = (await db.execute(select(func.count()).select_from(Agent))).scalar() or 0

    # Token 统计 (全局)
    token_result = (await db.execute(
        select(
            func.coalesce(func.sum(Session.input_tokens), 0),
            func.coalesce(func.sum(Session.output_tokens), 0),
            func.coalesce(func.sum(Session.total_tokens), 0),
            func.coalesce(func.sum(Session.estimated_cost_usd), 0),
        )
    )).one()

    # 今日 Token
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_tokens = (await db.execute(
        select(func.coalesce(func.sum(TokenUsageHourly.total_tokens_sum), 0)).where(
            TokenUsageHourly.hour >= today_start
        )
    )).scalar() or 0

    # 离线实例列表
    offline_result = await db.execute(
        select(Instance).where(Instance.status.in_(["offline", "unhealthy"]))
        .order_by(Instance.last_heartbeat.desc())
    )
    offline_list = [{
        "instance_id": inst.instance_id,
        "name": inst.name,
        "host": inst.host,
        "status": inst.status,
        "last_heartbeat": inst.last_heartbeat.isoformat() if inst.last_heartbeat else None,
    } for inst in offline_result.scalars().all()]

    # 最近 24h Token 趋势
    since_24h = datetime.utcnow() - timedelta(hours=24)
    trend_result = await db.execute(
        select(
            TokenUsageHourly.hour,
            func.sum(TokenUsageHourly.input_tokens_sum).label("input"),
            func.sum(TokenUsageHourly.output_tokens_sum).label("output"),
            func.sum(TokenUsageHourly.total_tokens_sum).label("total"),
        ).where(TokenUsageHourly.hour >= since_24h)
        .group_by(TokenUsageHourly.hour)
        .order_by(TokenUsageHourly.hour)
    )
    trend = [{
        "hour": row.hour.isoformat(),
        "input_tokens": row.input or 0,
        "output_tokens": row.output or 0,
        "total_tokens": row.total or 0,
    } for row in trend_result.all()]

    return {
        "instances": {
            "total": total_instances,
            "online": online_instances,
            "offline": offline_instances,
            "unhealthy": unhealthy_instances,
        },
        "agents": {
            "total": total_agents,
        },
        "tokens": {
            "total_input": token_result[0],
            "total_output": token_result[1],
            "total": token_result[2],
            "total_cost_usd": round(token_result[3], 4),
            "today_total": today_tokens,
        },
        "alerts": offline_list,
        "trend_24h": trend,
    }
