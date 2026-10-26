"""Lazy AgentService singleton for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from dotenv import load_dotenv

from backend.agents.service import AgentService

load_dotenv()


@lru_cache
def get_agent_service() -> AgentService:
    return AgentService()


def reset_agent_service() -> None:
    """Clear the singleton (e.g. after changing .env / API keys)."""
    get_agent_service.cache_clear()