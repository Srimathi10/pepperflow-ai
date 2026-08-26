"""Workflow builder — fluent API for constructing workflows."""

import uuid
from typing import Any, Dict, List, Optional


class StepBuilder:
    def __init__(self, name: str, step_type: str, **kwargs):
        self.id = str(uuid.uuid4())
        self.name = name
        self.step_type = step_type
        self.agent_name = kwargs.get("agent_name")
        self.config = kwargs.get("config", {})
        self.max_retries = kwargs.get("max_retries", 3)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "step_type": self.step_type,
            "agent_name": self.agent_name,
            "config": self.config,
            "max_retries": self.max_retries,
        }


class WorkflowBuilder:
    """Fluent builder for creating workflow definitions."""

    def __init__(self, name: str, description: str = ""):
        self._name = name
        self._description = description
        self._steps: List[StepBuilder] = []

    def step(self, name: str, agent: str, **config) -> "WorkflowBuilder":
        """Add an agent-executed step."""
        self._steps.append(StepBuilder(
            name=name,
            step_type="agent",
            agent_name=agent,
            config=config,
        ))
        return self

    def human_review(self, name: str = "human_review", approvers: Optional[List[str]] = None) -> "WorkflowBuilder":
        """Add a human-in-the-loop approval step."""
        self._steps.append(StepBuilder(
            name=name,
            step_type="human_review",
            config={"approvers": approvers or []},
        ))
        return self

    def conditional(self, name: str, condition: str, **kwargs) -> "WorkflowBuilder":
        """Add a conditional branching step."""
        self._steps.append(StepBuilder(
            name=name,
            step_type="conditional",
            config={"condition": condition, **kwargs},
        ))
        return self

    def build(self) -> Dict[str, Any]:
        """Build the workflow definition."""
        return {
            "name": self._name,
            "description": self._description,
            "steps": [s.to_dict() for s in self._steps],
        }
