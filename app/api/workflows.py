"""Workflow API routes."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.schemas import WorkflowCreate, WorkflowResponse, StepResponse, ApprovalRequest
from app.core.database import get_db
from app.models.workflow import Workflow, WorkflowStep, WorkflowStatus
from app.services.workflow_engine import WorkflowEngine
from app.services.audit_service import AuditService
from app.models.audit import AuditAction

router = APIRouter()


@router.post("", response_model=WorkflowResponse, status_code=201)
async def create_workflow(payload: WorkflowCreate, db: AsyncSession = Depends(get_db)):
    """Create a new workflow with steps."""
    workflow = Workflow(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        context=payload.context,
    )
    db.add(workflow)

    for i, step_data in enumerate(payload.steps):
        step = WorkflowStep(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            name=step_data.name,
            step_type=step_data.step_type,
            agent_name=step_data.agent_name,
            config=step_data.config,
            max_retries=step_data.max_retries,
            order=i,
        )
        db.add(step)

    audit = AuditService(db)
    await audit.log(workflow.id, AuditAction.WORKFLOW_CREATED)
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.get("", response_model=List[WorkflowResponse])
async def list_workflows(
    status: str = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """List workflows, optionally filtered by status."""
    query = select(Workflow).order_by(Workflow.created_at.desc()).limit(limit)
    if status:
        query = query.where(Workflow.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Get a workflow by ID."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.post("/{workflow_id}/execute", response_model=WorkflowResponse)
async def execute_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """Execute a workflow (or resume from HITL pause)."""
    engine = WorkflowEngine(db)
    try:
        workflow = await engine.execute(workflow_id)
        return workflow
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/approve", response_model=WorkflowResponse)
async def approve_step(
    workflow_id: str,
    payload: ApprovalRequest,
    db: AsyncSession = Depends(get_db),
):
    """Approve or deny a human-in-the-loop step and resume execution."""
    result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if workflow.status != WorkflowStatus.WAITING_APPROVAL:
        raise HTTPException(status_code=400, detail="Workflow is not waiting for approval")

    audit = AuditService(db)
    action = AuditAction.APPROVAL_GRANTED if payload.approved else AuditAction.APPROVAL_DENIED
    await audit.log(workflow.id, action, actor=payload.actor, details={"notes": payload.notes})

    if not payload.approved:
        workflow.status = WorkflowStatus.CANCELLED
        workflow.error = f"Denied by {payload.actor}: {payload.notes}"
        await db.commit()
        return workflow

    # Resume execution
    workflow.status = WorkflowStatus.DRAFT
    await db.commit()
    engine = WorkflowEngine(db)
    return await engine.execute(workflow_id)
