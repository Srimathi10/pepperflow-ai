"""Audit log model."""

import enum
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditAction(str, enum.Enum):
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_EXECUTED = "workflow_executed"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    RETRY_ATTEMPT = "retry_attempt"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=True)
    action = Column(Enum(AuditAction), nullable=False)
    actor = Column(String(255), default="system")
    details = Column(JSON, default=dict)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    workflow = relationship("Workflow", back_populates="audit_logs")
