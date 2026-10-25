"""Shared LangGraph state for one ticket.

One ticket = one LangGraph thread (thread_id = ticket id). The agents are fixed
graph nodes; each ticket just gets its own checkpointed session.
"""

from __future__ import annotations

import operator
from datetime import datetime, timezone
from typing import Annotated, Any, Literal, TypedDict

Team = Literal["network", "application", "finance"]
Status = Literal["new", "in_progress", "awaiting_user", "resolved", "escalated"]


class Ticket(TypedDict, total=False):
    id: str
    title: str
    description: str
    requester: str
    priority: str
    # Demo only: forces the mock network environment into a scenario
    # (see tools/network_tools.py SCENARIOS) regardless of the ticket text.
    mock_scenario: str


class ChatMessage(TypedDict):
    role: Literal["agent", "user"]
    author: str
    content: str
    at: str


class WorkNote(TypedDict):
    author: str
    note: str
    at: str


class TicketState(TypedDict, total=False):
    ticket: Ticket
    status: Status
    classification: dict[str, Any]
    team: Team

    # Append-only logs (LangGraph merges these with operator.add).
    chat: Annotated[list[ChatMessage], operator.add]
    work_notes: Annotated[list[WorkNote], operator.add]
    diagnostics: Annotated[list[dict[str, Any]], operator.add]

    kb_hits: list[dict[str, Any]]
    symptom: str
    findings: dict[str, Any]
    remediated: bool
    pending: dict[str, Any] | None  # what the agent is waiting on from the user
    last_user_reply: str
    next_step: str
    user_turns: int
    resolution: str | None
    escalation: dict[str, Any] | None


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def agent_msg(author: str, content: str) -> ChatMessage:
    return {"role": "agent", "author": author, "content": content, "at": now()}


def user_msg(author: str, content: str) -> ChatMessage:
    return {"role": "user", "author": author, "content": content, "at": now()}


def note(author: str, text: str) -> WorkNote:
    return {"author": author, "note": text, "at": now()}
