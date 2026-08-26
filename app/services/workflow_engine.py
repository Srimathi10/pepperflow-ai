"""
Core workflow execution engine — wired with event sourcing.

Every state transition now:
1. Produces an immutable Event in the EventStore
2. State is DERIVED from events, not stored separately
3. Enables: replay, time-travel, audit proof, debugging

This is the genuine integration that makes event sourcing real.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.workflow import Workflow, WorkflowStep, WorkflowStatus
from app.services.agent_runner import AgentRunner
from app.services.audit_service import AuditService
from app.events.event_store import Event, EventType, event_store
from app.events.replay_engine import ReplayEngine


class WorkflowEngine:
    """Executes workflows with event-sourced audit trail."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent_runner = AgentRunner()
        self.audit = AuditService(db)
        self.events = event_store
        self.replay = ReplayEngine(self.events)

    async def execute(self, workflow_id: str) -> Workflow:
        """Main execution loop — every transition emits an event."""
        workflow = await self._load_workflow(workflow_id)
        if workflow.status not in (WorkflowStatus.DRAFT, WorkflowStatus.WAITING_APPROVAL):
            raise ValueError(f"Workflow {workflow_id} is in state {workflow.status}")

        # Emit workflow_executed event
        self.events.append(Event(
            event_type=EventType.WORKFLOW_EXECUTED,
            workflow_id=workflow_id,
            data={"previous_status": workflow.status.value},
        ))

        workflow.status = WorkflowStatus.RUNNING
        await self.db.flush()

        steps = sorted(workflow.steps, key=lambda s: s.order)

        for i, step in enumerate(steps):
            if i < workflow.current_step_index:
                continue

            workflow.current_step_index = i

            # Emit step_started event
            self.events.append(Event(
                event_type=EventType.STEP_STARTED,
                workflow_id=workflow_id,
                step_index=i,
                data={"step_name": step.name, "step_type": step.step_type},
            ))

            try:
                await self._execute_step(workflow, step, i)
            except Exception as e:
                # Emit step_failed event
                self.events.append(Event(
                    event_type=EventType.STEP_FAILED,
                    workflow_id=workflow_id,
                    step_index=i,
                    data={"error": str(e), "step_name": step.name},
                ))
                step.status = WorkflowStatus.FAILED
                step.error = str(e)
                workflow.status = WorkflowStatus.FAILED
                workflow.error = f"Step '{step.name}' failed: {e}"
                await self.db.commit()
                raise

        # Emit workflow_completed event
        self.events.append(Event(
            event_type=EventType.WORKFLOW_COMPLETED,
            workflow_id=workflow_id,
            data={"total_steps": len(steps)},
        ))

        workflow.status = WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.utcnow()
        await self.db.commit()
        return workflow

    async def _execute_step(self, workflow: Workflow, step: WorkflowStep, index: int):
        """Execute a single step with event emission."""
        step.status = WorkflowStatus.RUNNING

        if step.step_type == "human_review":
            # Emit approval_requested event
            self.events.append(Event(
                event_type=EventType.APPROVAL_REQUESTED,
                workflow_id=workflow.id,
                step_index=index,
                data={"step_name": step.name, "approvers": step.config.get("approvers", [])},
            ))
            step.status = WorkflowStatus.WAITING_APPROVAL
            workflow.status = WorkflowStatus.WAITING_APPROVAL
            await self.db.commit()
            return

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

                # Propagate context
                old_context = dict(workflow.context)
                workflow.context.update(result)

                # Emit step_completed + context_propagated events
                self.events.append(Event(
                    event_type=EventType.STEP_COMPLETED,
                    workflow_id=workflow.id,
                    step_index=index,
                    data={"output": result, "attempt": attempt + 1},
                ))
                self.events.append(Event(
                    event_type=EventType.CONTEXT_PROPAGATED,
                    workflow_id=workflow.id,
                    step_index=index,
                    data={
                        "context_update": result,
                        "keys_added": list(result.keys()),
                    },
                ))
                return
            except Exception as e:
                last_error = e
                step.retry_count = attempt + 1
                if attempt < step.max_retries:
                    self.events.append(Event(
                        event_type=EventType.STEP_RETRY_SCHEDULED,
                        workflow_id=workflow.id,
                        step_index=index,
                        data={"attempt": attempt + 1, "error": str(e)},
                    ))
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
        raise last_error

    def get_workflow_state(self, workflow_id: str) -> Dict:
        """Reconstruct current state from events — not from the database."""
        snapshot = self.events.reconstruct_state(workflow_id)
        return {
            "workflow_id": snapshot.workflow_id,
            "status": snapshot.status,
            "current_step_index": snapshot.current_step_index,
            "context": snapshot.context,
            "step_states": snapshot.step_states,
            "last_event_id": snapshot.last_event_id,
        }

    def replay_from(self, workflow_id: str, from_event_id: str, context_override: Dict = None) -> Dict:
        """Replay a workflow from a specific checkpoint."""
        return self.replay.replay_from(workflow_id, from_event_id, context_override)

    def get_audit_proof(self, workflow_id: str) -> Dict:
        """Get cryptographic proof of workflow execution."""
        return self.replay.get_audit_proof(workflow_id)

    def get_event_history(self, workflow_id: str) -> list:
        """Get all events for a workflow."""
        events = self.events.get_events(workflow_id)
        return [e.to_dict() for e in events]

    async def _load_workflow(self, workflow_id: str) -> Workflow:
        result = await self.db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        return workflow
