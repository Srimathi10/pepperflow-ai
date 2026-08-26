"""Human-in-the-Loop manager with approval gates, timeouts, and delegation."""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.workflow import Workflow, WorkflowStep, WorkflowStatus
from app.models.audit import AuditLog, AuditAction

logger = structlog.get_logger()


class HITLManager:
    def __init__(self, db: AsyncSession, timeout_seconds: int = 3600):
        self.db = db
        self.timeout_seconds = timeout_seconds

    async def request_approval(self, workflow: Workflow, step: WorkflowStep, approvers: List[str]) -> Dict:
        approval_id = str(uuid.uuid4())
        step.status = WorkflowStatus.WAITING_APPROVAL
        step.config["approval_id"] = approval_id
        step.config["approvers"] = approvers
        step.config["timeout_at"] = (datetime.utcnow() + timedelta(seconds=self.timeout_seconds)).isoformat()
        workflow.status = WorkflowStatus.WAITING_APPROVAL

        self.db.add(AuditLog(
            id=str(uuid.uuid4()), workflow_id=workflow.id,
            action=AuditAction.APPROVAL_REQUESTED,
            details={"step": step.name, "approval_id": approval_id, "approvers": approvers},
        ))
        await self.db.commit()
        return {"approval_id": approval_id, "timeout_at": step.config["timeout_at"]}

    async def approve(self, workflow: Workflow, approval_id: str, approved: bool, actor: str, notes: str = "") -> Workflow:
        step = next((s for s in workflow.steps if s.status == WorkflowStatus.WAITING_APPROVAL and s.config.get("approval_id") == approval_id), None)
        if not step:
            raise ValueError("No matching approval request found")

        action = AuditAction.APPROVAL_GRANTED if approved else AuditAction.APPROVAL_DENIED
        self.db.add(AuditLog(id=str(uuid.uuid4()), workflow_id=workflow.id, action=action, actor=actor,
            details={"step": step.name, "notes": notes}))

        if not approved:
            workflow.status = WorkflowStatus.CANCELLED
            workflow.error = f"Denied by {actor}: {notes}"
        else:
            step.status = WorkflowStatus.COMPLETED
            step.completed_at = datetime.utcnow()
            workflow.status = WorkflowStatus.DRAFT
            workflow.current_step_index += 1

        await self.db.commit()
        return workflow

    async def check_timeouts(self) -> List[str]:
        result = await self.db.execute(select(Workflow).where(Workflow.status == WorkflowStatus.WAITING_APPROVAL))
        timed_out = []
        for wf in result.scalars().all():
            step = next((s for s in wf.steps if s.status == WorkflowStatus.WAITING_APPROVAL), None)
            if step and step.config.get("timeout_at"):
                if datetime.utcnow() > datetime.fromisoformat(step.config["timeout_at"]):
                    wf.status = WorkflowStatus.FAILED
                    wf.error = "Approval timeout"
                    timed_out.append(wf.id)
        if timed_out:
            await self.db.commit()
        return timed_out
