"""Tests for workflow API."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_workflow(client):
    payload = {
        "name": "test-workflow",
        "description": "A test workflow",
        "steps": [
            {"name": "step1", "step_type": "agent", "agent_name": "test_agent"},
            {"name": "review", "step_type": "human_review"},
        ],
    }
    response = await client.post("/api/v1/workflows", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-workflow"
    assert data["status"] == "draft"


@pytest.mark.asyncio
async def test_list_workflows(client):
    response = await client.get("/api/v1/workflows")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
