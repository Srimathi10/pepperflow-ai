# PepperFlow AI

**Agentic Workflow Automation Platform**

AI agents that understand business processes and execute multi-step workflows with human oversight.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   FastAPI    │────▶│  LangGraph   │────▶│  PostgreSQL  │
│   Gateway    │     │  Orchestrator│     │  + Redis     │
└─────────────┘     └──────────────┘     └─────────────┘
       │                   │                    │
       ▼                   ▼                    ▼
  ┌─────────┐      ┌───────────┐       ┌───────────┐
  │  REST   │      │ Tool Calls│       │  Audit    │
  │  API    │      │ + Retries │       │  Logs     │
  └─────────┘      └───────────┘       └───────────┘
```

## Features

- **LangGraph-style orchestration** — Multi-step workflow execution with state management
- **Human-in-the-loop approvals** — Pause workflows for manual review
- **Tool calling** — LLM-driven function execution
- **Automatic retries** — Configurable retry policies with backoff
- **Audit logging** — Complete trail of every workflow action
- **Workflow templates** — Pre-built patterns for common business processes

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, LangGraph, LangChain
- **Database:** PostgreSQL 15+ (workflow state), Redis 7+ (caching, queues)
- **Infrastructure:** Docker, Docker Compose
- **Testing:** pytest, httpx

## Quick Start

```bash
git clone https://github.com/YOUR_USERNAME/pepperflow-ai.git
cd pepperflow-ai
cp .env.example .env
docker compose up -d
# Visit http://localhost:8000/docs
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/workflows` | Create a new workflow |
| GET | `/api/v1/workflows/{id}` | Get workflow status |
| POST | `/api/v1/workflows/{id}/execute` | Execute a workflow |
| POST | `/api/v1/workflows/{id}/approve` | Approve a HITL step |
| GET | `/api/v1/audit` | Query audit logs |

## License

MIT
