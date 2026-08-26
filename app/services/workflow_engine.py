"""Core workflow execution engine with LangGraph-style orchestration."""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.workflow import Workflow, WorkflowStep, WorkflowStatus
from app.models.audit import AuditLog, AuditAction
from app.services.agent_runner import AgentRunner
from app.services.audit_service import AuditService


class WorkflowEngine:
    """Executes workflows step-by-step with retry logic and HITL support."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent_runner = AgentRunner()
        self.audit = AuditService(db)

    async def execute(self, workflow_id: str) -> Workflow:
        """Main execution loop for a workflow."""
        workflow = await self._load_workflow(workflow_id)
        if workflow.status not in (WorkflowStatus.DRAFT, WorkflowStatus.WAITING_APPROVAL):
            raise ValueError(f"Workflow {workflow_id} is in state {workflow.status}, cannot execute")

        workflow.status = WorkflowStatus.RUNNING
        await self.audit.log(workflow.id, AuditAction.WORKFLOW_EXECUTED)

        steps = sorted(workflow.steps, key=lambda s: s.order)

        for i, step in enumerate(steps):
            if i < workflow.current_step_index:
                continue  # Skip already-completed steps

            workflow.current_step_index = i
            await self.db.flush()

            try:
                await self._execute_step(workflow, step)
            except Exception as e:
                step.status = WorkflowStatus.FAILED
                step.error = str(e)
                workflow.status = WorkflowStatus.FAILED
                workflow.error = f"Step '{step.name}' failed: {e}"
                await self.audit.log(
                    workflow.id, AuditAction.WORKFLOW_FAILED,
                    details={"step": step.name, "error": str(e)}
                )
                await self.db.commit()
                raise

        workflow.status = WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.utcnow()
        await self.audit.log(workflow.id, AuditAction.WORKFLOW_COMPLETED)
        await self.db.commit()
        return workflow

    async def _execute_step(self, workflow: Workflow, step: WorkflowStep):
        """Execute a single workflow step with retry logic."""
        step.status = WorkflowStatus.RUNNING
        await self.audit.log(workflow.id, AuditAction.STEP_STARTED, details={"step": step.name})

        if step.step_type == "human_review":
            step.status = WorkflowStatus.WAITING_APPROVAL
            workflow.status = WorkflowStatus.WAITING_APPROVAL
            await self.audit.log(
                workflow.id, AuditAction.APPROVAL_REQUESTED,
                details={"step": step.name, "config": step.config}
            )
            await self.db.commit()
            return  # Pause execution

        # Execute with retries
        last_error = None
        for attempt in range(step.max_retries + 1):
            try:
                result = await self.agent_runner.run(
                    agent_name=step.agent_name or "default",
                    input_data=workflow.context,
                    step_config=step.config,
                )
                step.output = result
                step.status = WorkflowStatus.COMPLETED
                step.completed_at = datetime.utcnow()
                workflow.context.update(result)  # Propagate outputs
                await self.audit.log(
                    workflow.id, AuditAction.STEP_COMPLETED,
                    details={"step": step.name, "attempt": attempt + 1}
                )
                return
            except Exception as e:
                last_error = e
                step.retry_count = attempt + 1
                if attempt < step.max_retries:
                    await self.audit.log(
                        workflow.id, AuditAction.RETRY_ATTEMPT,
                        details={"step": step.name, "attempt": attempt + 1, "error": str(e)}
                    )
                    import asyncio
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        raise last_error

    async def _load_workflow(self, workflow_id: str) -> Workflow:
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id).execution_options(
                loader_strategy=Workflow.steps
            )
        )
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        return workflow
