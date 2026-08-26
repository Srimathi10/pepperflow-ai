"""
Event-Sourced Audit Trail — the genuine architectural invention.

This is NOT a logging system. It is a full event-sourcing implementation where:
1. Every state transition produces an immutable Event
2. Events are append-only (never updated or deleted)
3. Current state is derived by replaying events
4. Any point-in-time state can be reconstructed
5. Workflows can be replayed from any checkpoint

WHY THIS MATTERS:
- Most audit systems just record "what happened". This records "what happened"
  in a way that is mathematically reconstructable.
- Enables workflow debugging: "Show me the exact state at step 3 before the failure"
- Enables compliance: "Prove that no step was skipped"
- Enables replay: "Re-run this workflow from the approval step with different context"
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import json
import structlog

logger = structlog.get_logger()


class EventType(str, Enum):
    """All possible events in the system. Adding a new event type is a 
    deliberate, reviewable change — not a side effect."""
    WORKFLOW_CREATED = "workflow_created"
    WORKFLOW_EXECUTED = "workflow_executed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_RETRY_SCHEDULED = "step_retry_scheduled"
    CONTEXT_PROPAGATED = "context_propagated"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_GRANTED = "approval_granted"
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_TIMEOUT = "approval_timeout"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_REPLAYED = "workflow_replayed"


@dataclass(frozen=True)  # Immutable!
class Event:
    """An immutable event. Once created, it can never be modified.
    This is the core guarantee of event sourcing."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    workflow_id: str = ""
    step_index: int = -1
    actor: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict) -> "Event":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class WorkflowSnapshot:
    """A point-in-time snapshot of workflow state, reconstructed from events."""
    workflow_id: str
    status: str
    current_step_index: int
    context: Dict[str, Any]
    step_states: Dict[int, str]  # step_index -> status
    last_event_id: str
    reconstructed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class EventStore:
    """
    The genuine invention: an append-only event store that supports:
    1. Appending events (never modifying)
    2. Reconstructing state by replaying events
    3. Time-travel queries (state at any point in time)
    4. Workflow replay from any checkpoint
    """

    def __init__(self):
        # In production: this would be PostgreSQL with append-only table
        # For demonstration: in-memory store with persistence
        self._events: Dict[str, List[Event]] = {}  # workflow_id -> [events]
        self._event_index: Dict[str, Event] = {}   # event_id -> event

    def append(self, event: Event) -> Event:
        """Append an event. Never modify existing events."""
        if event.workflow_id not in self._events:
            self._events[event.workflow_id] = []
        self._events[event.workflow_id].append(event)
        self._event_index[event.event_id] = event
        logger.info("event.appended", event_type=event.event_type, 
                    workflow_id=event.workflow_id, event_id=event.event_id)
        return event

    def get_events(self, workflow_id: str) -> List[Event]:
        """Get all events for a workflow, in order."""
        return list(self._events.get(workflow_id, []))

    def get_events_until(self, workflow_id: str, event_id: str) -> List[Event]:
        """Get events up to (and including) a specific event. For time-travel."""
        events = self.get_events(workflow_id)
        result = []
        for e in events:
            result.append(e)
            if e.event_id == event_id:
                break
        return result

    def reconstruct_state(self, workflow_id: str) -> WorkflowSnapshot:
        """Reconstruct current state by replaying all events.
        
        This is the key insight: instead of storing state and trying to keep
        it consistent, we store events and derive state. The events are the
        source of truth, not the state.
        """
        events = self.get_events(workflow_id)
        if not events:
            raise ValueError(f"No events found for workflow {workflow_id}")

        state = {
            "status": "unknown",
            "current_step_index": 0,
            "context": {},
            "step_states": {},
        }

        for event in events:
            state = self._apply_event(state, event)

        return WorkflowSnapshot(
            workflow_id=workflow_id,
            status=state["status"],
            current_step_index=state["current_step_index"],
            context=state["context"],
            step_states=state["step_states"],
            last_event_id=events[-1].event_id if events else "",
        )

    def reconstruct_at_event(self, workflow_id: str, event_id: str) -> WorkflowSnapshot:
        """Reconstruct state at a specific point in time (time-travel)."""
        events = self.get_events_until(workflow_id, event_id)
        if not events:
            raise ValueError(f"No events found up to {event_id}")

        state = {
            "status": "unknown",
            "current_step_index": 0,
            "context": {},
            "step_states": {},
        }
        for event in events:
            state = self._apply_event(state, event)

        return WorkflowSnapshot(
            workflow_id=workflow_id,
            status=state["status"],
            current_step_index=state["current_step_index"],
            context=state["context"],
            step_states=state["step_states"],
            last_event_id=event_id,
        )

    def get_replay_from(self, workflow_id: str, from_event_id: str) -> List[Event]:
        """Get events from a specific point for replay.
        
        This enables: "Re-run this workflow from the approval step"
        by getting all events after the approval event and replaying them
        with modified context.
        """
        events = self.get_events(workflow_id)
        found = False
        result = []
        for e in events:
            if found:
                result.append(e)
            if e.event_id == from_event_id:
                found = True
        return result

    def compute_diff(self, workflow_id: str, event_id_a: str, event_id_b: str) -> Dict:
        """Compare two points in time. What changed between event A and event B?
        
        This is useful for debugging: "What changed between the first attempt
        and the retry that succeeded?"
        """
        state_a = self.reconstruct_at_event(workflow_id, event_id_a)
        state_b = self.reconstruct_at_event(workflow_id, event_id_b)

        diff = {
            "status_changed": state_a.status != state_b.status,
            "old_status": state_a.status,
            "new_status": state_b.status,
            "step_index_changed": state_a.current_step_index != s
