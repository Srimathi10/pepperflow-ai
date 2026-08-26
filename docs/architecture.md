# System Architecture — PepperFlow AI

## Overview

PepperFlow AI is an agentic workflow automation platform that uses event-sourced audit trails and a deterministic replay engine to provide human-in-the-loop workflow execution with complete auditability.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    API LAYER (FastAPI)                            │
│  REST endpoints + WebSocket for real-time workflow updates        │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│               WORKFLOW ENGINE (Core)                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ Workflow      │  │ LLM Orchestrator │  │ Tool Registry    │   │
│  │ Executor      │→ │ (GPT-4o)         │→ │ (External APIs)  │   │
│  └──────────────┘  └──────────────────┘  └──────────────────┘   │
│         │                    │                     │             │
│         ▼                    ▼                     ▼             │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ Event Store   │  │ HITL Manager     │  │ Circuit Breaker  │   │
│  │ (Immutable)   │  │ (Approvals)      │  │ (Retry Logic)    │   │
│  └──────────────┘  └──────────────────┘  └──────────────────┘   │
└──────────────────────┬───────────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                     │
│  PostgreSQL (workflows, events, state) + Redis (caching)         │
└──────────────────────────────────────────────────────────────────┘
```

## Core Invention: Event-Sourced Audit Trail

### The Problem
Most workflow engines log events but can't prove what happened. If a workflow fails at step 3 of 5, you can't reliably determine:
- What state the workflow was in at step 2
- What data was passed between steps
- Whether step 1's output was correct

### Our Solution
An immutable event store where every state transition is recorded as an append-only event with a hash chain for tamper-evidence:

```python
@dataclass
class WorkflowEvent:
    event_id: str
    workflow_id: str
    event_type: EventType  # STEP_STARTED, STEP_COMPLETED, etc.
    step_id: str
    data: Dict[str, Any]
    timestamp: datetime
    hash_chain: str  # SHA-256 of previous event hash + this event
```

### Replay Engine
Given an event stream, the replay engine can:
1. Reconstruct workflow state at any point in time
2. Compare two snapshots to identify divergence
3. Re-execute from a checkpoint with different inputs

This enables debugging workflows by "time-traveling" to any point.

## Test Coverage

```
Name                                    Stmts   Miss  Cover
------------------------------------------------------------
app/event_store.py                         85      0   100%
app/replay_engine.py                       62      0   100%
------------------------------------------------------------
TOTAL                                     147      0   100%
```

22 unit tests covering event creation, hash chain verification, state reconstruction, replay, and circuit breaker patterns.
