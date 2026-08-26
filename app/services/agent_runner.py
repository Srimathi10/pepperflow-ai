"""Agent execution service — runs LLM agents with tool calling."""

import structlog
from typing import Any, Dict

from openai import AsyncOpenAI

from app.core.config import settings

logger = structlog.get_logger()


class AgentRunner:
    """Runs an agent step by calling the configured LLM with tool support."""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def run(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        step_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute an agent step."""
        system_prompt = step_config.get("system_prompt", f"You are agent '{agent_name}'.")
        user_message = step_config.get("user_message_template", "Process the following input:")
        tools = step_config.get("tools", [])

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_message}\n\nContext: {input_data}"},
        ]

        logger.info("agent.run.start", agent=agent_name, model=settings.LLM_MODEL)

        kwargs = {
            "model": settings.LLM_MODEL,
            "messages": messages,
            "temperature": step_config.get("temperature", 0.1),
        }

        if tools:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]

        # Handle tool calls
        if choice.message.tool_calls:
            tool_results = await self._execute_tools(choice.message.tool_calls)
            return {
                "agent": agent_name,
                "response": choice.message.content,
                "tool_calls": [tc.function.name for tc in choice.message.tool_calls],
                "tool_results": tool_results,
                "tokens_used": response.usage.total_tokens,
            }

        return {
            "agent": agent_name,
            "response": choice.message.content,
            "tokens_used": response.usage.total_tokens,
        }

    async def _execute_tools(self, tool_calls) -> list:
        """Execute tool calls and return results."""
        results = []
        for tc in tool_calls:
            logger.info("agent.tool.execute", tool=tc.function.name)
            # Tool execution would be dispatched to registered tool handlers
            results.append({
                "tool": tc.function.name,
                "status": "executed",
                "result": f"Tool {tc.function.name} executed successfully",
            })
        return results
