from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import get_current_user
from ..database import get_db
from ..models import Agent, Session, Instance

router = APIRouter(prefix="/api/ranks", tags=["ranks"], dependencies=[Depends(get_current_user)])

# 官阶定义：(rank_id, 名称, emoji, 英文名, 最大人数(累计上限))
RANK_TIERS = [
    (0, "皇帝", "👑", "Emperor", 1),
    (1, "一品·太师", "🐉", "1st Rank", 3),
    (2, "二品·总督", "🦁", "2nd Rank", 6),
    (3, "三品·按察使", "🐯", "3rd Rank", 10),
    (4, "四品·知府", "🦅", "4th Rank", 16),
    (5, "五品·同知", "🐎", "5th Rank", 24),
    (6, "六品·通判", "🐂", "6th Rank", 34),
    (7, "七品·知县", "🐏", "7th Rank", 47),
    (8, "八品·县丞", "🐓", "8th Rank", 63),
    (9, "九品·巡检", "🐿️", "9th Rank", 9999),
]


def _assign_rank(position: int) -> dict:
    """根据排名位置分配官阶"""
    for rank_id, name_zh, emoji, name_en, max_pos in RANK_TIERS:
        if position <= max_pos:
            return {
                "rank_id": rank_id,
                "rank_name": name_zh,
                "rank_name_en": name_en,
                "rank_emoji": emoji,
            }
    last = RANK_TIERS[-1]
    return {"rank_id": last[0], "rank_name": last[1], "rank_name_en": last[3], "rank_emoji": last[2]}


@router.get("")
async def get_ranks(db: AsyncSession = Depends(get_db)):
    """根据 Agent Token 用量排名，分配官阶"""

    # 查询每个 agent 的 token 总量
    result = await db.execute(
        select(
            Session.instance_id,
            Session.agent_id,
            func.sum(Session.total_tokens).label("total_tokens"),
            func.sum(Session.estimated_cost_usd).label("cost"),
            func.count().label("session_count"),
        ).group_by(Session.instance_id, Session.agent_id)
        .order_by(func.sum(Session.total_tokens).desc())
    )
    rows = result.all()

    agents = []
    for idx, row in enumerate(rows):
        # 获取 agent 名称和 emoji
        agent_info = (await db.execute(
            select(Agent.name, Agent.identity_emoji).where(
                Agent.instance_id == row.instance_id,
                Agent.agent_id == row.agent_id,
            )
        )).first()
        agent_name = (agent_info.name if agent_info else None) or row.agent_id
        agent_emoji = (agent_info.identity_emoji if agent_info else None) or ""

        # 获取实例名称
        instance_name = (await db.execute(
            select(Instance.name).where(Instance.instance_id == row.instance_id)
        )).scalar() or row.instance_id

        rank = _assign_rank(idx + 1)
        agents.append({
            **rank,
            "position": idx + 1,
            "agent_id": row.agent_id,
            "instance_id": row.instance_id,
            "instance_name": instance_name,
            "agent_name": agent_name,
            "agent_emoji": agent_emoji,
            "total_tokens": row.total_tokens or 0,
            "estimated_cost_usd": round(row.cost or 0, 4),
            "session_count": row.session_count or 0,
        })

    # 按官阶分组
    tiers = []
    for rank_id, name_zh, emoji, name_en, _ in RANK_TIERS:
        tier_agents = [a for a in agents if a["rank_id"] == rank_id]
        if tier_agents:
            tiers.append({
                "rank_id": rank_id,
                "rank_name": name_zh,
                "rank_name_en": name_en,
                "rank_emoji": emoji,
                "agents": tier_agents,
            })

    return {"tiers": tiers, "total_agents": len(agents)}
