"""LangGraph agents: orchestrator, Network agent, Application/Finance stubs.

Public entry point for the backend: `AgentService` (see service.py).
"""

from .config import AgentSettings, load_settings

__all__ = ["AgentSettings", "load_settings", "AgentService"]


def __getattr__(name):  # lazy, so pure modules import without LangGraph installed
    if name == "AgentService":
        from .service import AgentService

        return AgentService
    raise AttributeError(name)
