"""Optional LLM access. Every caller must handle `None` (rules-only mode)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from .config import AgentSettings

log = logging.getLogger(__name__)

_DEFAULT_MODELS = {"anthropic": "claude-sonnet-4-5", "openai": "gpt-4o-mini"}


def get_chat_model(settings: AgentSettings) -> Any | None:
    provider = settings.llm_provider
    if provider in ("", "none"):
        return None
    model = settings.llm_model or _DEFAULT_MODELS.get(provider)
    try:
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=model, temperature=0)
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=model, temperature=0)
    except Exception as exc:  # missing package or API key
        log.warning("LLM provider %r unavailable (%s); using rules only", provider, exc)
        return None
    log.warning("Unknown AGENT_LLM_PROVIDER %r; using rules only", provider)
    return None


def ask_text(llm: Any | None, system: str, prompt: str) -> str | None:
    """Return the model's text reply, or None if there is no model or it fails."""
    if llm is None:
        return None
    try:
        reply = llm.invoke([("system", system), ("human", prompt)])
    except Exception as exc:
        log.warning("LLM call failed (%s); falling back to rules", exc)
        return None
    content = getattr(reply, "content", reply)
    if isinstance(content, list):  # Anthropic content blocks
        content = "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content)
    return str(content).strip() or None


def ask_json(llm: Any | None, system: str, prompt: str) -> dict[str, Any] | None:
    text = ask_text(llm, system + "\nRespond with a single JSON object only.", prompt)
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def polish(llm: Any | None, message: str, audience: str = "an employee") -> str:
    """Let the LLM make a templated message friendlier; keep the template if not."""
    better = ask_text(
        llm,
        f"You rewrite IT support messages for {audience}. Keep every instruction, "
        "command and ticket detail exactly. Be concise and friendly. No sign-off.",
        message,
    )
    return better or message
