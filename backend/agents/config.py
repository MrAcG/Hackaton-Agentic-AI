"""Runtime settings for the agent layer, read from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AgentSettings:
    # "anthropic", "openai" or "none". With "none" every agent runs on
    # deterministic rules, which keeps the demo and the tests reproducible.
    llm_provider: str = "none"
    llm_model: str | None = None
    kb_dir: Path = REPO_ROOT / "data" / "kb"
    # How many times an agent may ask the employee something before escalating.
    max_user_turns: int = 3
    # Below this, the orchestrator still routes but flags the ticket for review.
    min_route_confidence: float = 0.5


def load_settings() -> AgentSettings:
    return AgentSettings(
        llm_provider=os.getenv("AGENT_LLM_PROVIDER", "none").strip().lower(),
        llm_model=os.getenv("AGENT_LLM_MODEL") or None,
        kb_dir=Path(os.getenv("AGENT_KB_DIR", str(REPO_ROOT / "data" / "kb"))),
        max_user_turns=int(os.getenv("AGENT_MAX_USER_TURNS", "3")),
        min_route_confidence=float(os.getenv("AGENT_MIN_ROUTE_CONFIDENCE", "0.5")),
    )
