"""Workflow database models."""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, JSON, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class WorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.DRAFT, nullable=False)
    current_step_index = Column(Integer, default=0)
    context = Column(JSON, default=dict)
    result = Column(JSON, default=dict)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    steps = relationship("WorkflowStep", back_populates="workflow", order_by="WorkflowStep.order")
    audit_logs = relationship("AuditLog", back_populates="workflow")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    name = Column(String(255), nullable=False)
    step_type = Column(String(50), nullable=False)  # agent, human_review, conditional
    agent_name = Column(String(255), nullable=True)
    config = Column(JSON, default=dict)
    order = Column(Integer, nullable=False)
    status = Column(Enum(WorkflowStatus), default=WorkflowStatus.DRAFT)
    output = Column(JSON, default=dict)
    error = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow", back_populates="steps")


class WorkflowState(Base):
    """LangGraph-compatible state snapshots."""
    __tablename__ = "workflow_states"

    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    state_data = Column(JSON, nullable=False)
    version = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
