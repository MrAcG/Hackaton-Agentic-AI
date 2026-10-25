"""Lazy AgentService singleton for FastAPI routes."""

from __future__ import annotations

from functools import lru_cache

from backend.agents.service import AgentService


@lru_cache
def get_agent_service() -> AgentService:
    return AgentService()