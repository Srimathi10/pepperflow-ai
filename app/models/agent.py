"""Agent registry model."""

from datetime import datetime

from sqlalchemy import Column, String, DateTime, JSON, Boolean, Text

from app.core.database import Base


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, default="")
    agent_type = Column(String(50), nullable=False)  # llm, tool, hybrid
    model = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=True)
    tools = Column(JSON, default=list)
    config = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
