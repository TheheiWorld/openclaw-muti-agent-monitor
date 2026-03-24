from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Index, Text,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Instance(Base):
    __tablename__ = "instances"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(128), nullable=False)
    hostname = Column(String(256), default="")
    host = Column(String(256), nullable=False)
    port = Column(Integer, default=18789)
    status = Column(String(16), default="online")  # online / offline / unhealthy
    version = Column(String(32), default="")
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class Agent(Base):
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(String(64), nullable=False, index=True)
    agent_id = Column(String(64), nullable=False)
    name = Column(String(128), default="")
    identity_emoji = Column(String(16), default="")
    identity_theme = Column(String(32), default="")
    status = Column(String(16), default="active")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("ix_agent_instance_agent", "instance_id", "agent_id", unique=True),
    )


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(String(64), nullable=False)
    agent_id = Column(String(64), nullable=False)
    session_id = Column(String(128), nullable=False)
    session_key = Column(String(256), default="")
    channel = Column(String(32), default="")
    display_name = Column(String(128), default="")
    status = Column(String(16), default="")  # running / done / failed / killed / timeout
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    context_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)
    model_provider = Column(String(64), default="")
    model = Column(String(64), default="")
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    __table_args__ = (
        Index("ix_session_instance", "instance_id"),
        Index("ix_session_agent", "agent_id"),
        Index("ix_session_unique", "instance_id", "session_id", unique=True),
    )


class TokenUsageHourly(Base):
    __tablename__ = "token_usage_hourly"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(String(64), nullable=False)
    agent_id = Column(String(64), nullable=False)
    hour = Column(DateTime, nullable=False)  # 精确到小时
    input_tokens_sum = Column(Integer, default=0)
    output_tokens_sum = Column(Integer, default=0)
    total_tokens_sum = Column(Integer, default=0)
    session_count = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_token_hour", "hour"),
        Index("ix_token_instance_hour", "instance_id", "hour"),
        Index("ix_token_unique", "instance_id", "agent_id", "hour", unique=True),
    )


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
