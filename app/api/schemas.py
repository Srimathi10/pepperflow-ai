"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StepCreate(BaseModel):
    name: str
    step_type: str = "agent"
    agent_name: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    max_retries: int = 3


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    steps: List[StepCreate] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str
    current_step_index: int
    context: Dict[str, Any]
    result: Dict[str, Any]
    error: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class StepResponse(BaseModel):
    id: str
    name: str
    step_type: str
    agent_name: Optional[str]
    status: str
    output: Dict[str, Any]
    error: Optional[str]
    retry_count: int

    class Config:
        from_attributes = True


class ApprovalRequest(BaseModel):
    approved: bool
    notes: str = ""
    actor: str = "anonymous"


class AuditLogResponse(BaseModel):
    id: str
    workflow_id: Optional[str]
    action: str
    actor: str
    details: Dict[str, Any]
    error: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AgentCreate(BaseModel):
    name: str
    description: str = ""
    agent_type: str = "llm"
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: List[Dict[str, Any]] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
