"""Agent registry API routes."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.schemas import AgentCreate
from app.core.database import get_db
from app.models.agent import Agent

router = APIRouter()


@router.get("", response_model=List[dict])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.is_active == True))
    agents = result.scalars().all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "description": a.description,
            "agent_type": a.agent_type,
            "model": a.model,
            "tools": a.tools,
            "is_active": a.is_active,
        }
        for a in agents
    ]


@router.post("", status_code=201)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(
        id=str(uuid.uuid4()),
        name=payload.name,
        description=payload.description,
        agent_type=payload.agent_type,
        model=payload.model,
        system_prompt=payload.system_prompt,
        tools=payload.tools,
        config=payload.config,
    )
    db.add(agent)
    await db.commit()
    return {"id": agent.id, "name": agent.name}
