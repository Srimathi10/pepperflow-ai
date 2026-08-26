"""Audit logging service."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, AuditAction


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        workflow_id: Optional[str],
        action: AuditAction,
        actor: str = "system",
        details: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        entry = AuditLog(
            id=str(uuid.uuid4()),
            workflow_id=workflow_id,
            action=action,
            actor=actor,
            details=details or {},
            error=error,
            created_at=datetime.utcnow(),
        )
        self.db.add(entry)
        await self.db.flush()
        return entry
