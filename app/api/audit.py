"""Audit log API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.schemas import AuditLogResponse
from app.core.database import get_db
from app.models.audit import AuditLog

router = APIRouter()


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    workflow_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Query audit logs with optional filters."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if workflow_id:
        query = query.where(AuditLog.workflow_id == workflow_id)
    if action:
        query = query.where(AuditLog.action == action)
    result = await db.execute(query)
    return result.scalars().all()
