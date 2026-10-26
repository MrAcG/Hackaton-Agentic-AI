"""Map AgentService TicketView <-> portal ITSM shapes."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models import Message, Ticket, WorkNote, utcnow
from backend.agents.teams import TEAM_CATEGORY, TEAM_LABEL

STATUS_TO_PORTAL = {
    "new": "New",
    "in_progress": "In Progress",
    "awaiting_user": "Pending",
    "resolved": "Resolved",
    "escalated": "Escalated",
}

TEAM_TO_GROUP = {team: label for team, label in TEAM_LABEL.items()}
TEAM_TO_CATEGORY = dict(TEAM_CATEGORY)
GROUP_ASSIGNEE = {label: f"{label} Agent" for label in TEAM_LABEL.values()}


def _parse_at(value: str | None) -> datetime:
    if not value:
        return utcnow()
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return utcnow()


def _stable_id(prefix: str, ticket_id: str, key: str) -> str:
    digest = hashlib.sha1(f"{ticket_id}:{key}".encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def apply_agent_view(db: Session, ticket: Ticket, view: dict[str, Any]) -> None:
    """Update ticket fields and replace agent-origin chat/notes from TicketView."""
    status = view.get("status") or "in_progress"
    if view.get("awaiting_user"):
        status = "awaiting_user"
    ticket.state = STATUS_TO_PORTAL.get(status, "In Progress")

    team = view.get("team")
    if team in TEAM_TO_GROUP:
        ticket.assignment_group = TEAM_TO_GROUP[team]
        ticket.assigned_to = GROUP_ASSIGNEE[ticket.assignment_group]
        if team in TEAM_TO_CATEGORY:
            ticket.category = TEAM_TO_CATEGORY[team]

    ticket.updated_at = utcnow()

    db.query(Message).filter(Message.ticket_id == ticket.id, Message.origin == "agent").delete()
    db.query(WorkNote).filter(WorkNote.ticket_id == ticket.id, WorkNote.origin == "agent").delete()

    for index, item in enumerate(view.get("chat") or []):
        role = item.get("role")
        portal_role = "employee" if role == "user" else "agent"
        key = f"chat:{index}:{portal_role}:{item.get('content', '')}"
        db.add(
            Message(
                id=_stable_id("msg", ticket.id, key),
                ticket_id=ticket.id,
                role=portal_role,
                author=item.get("author") or ("Employee" if portal_role == "employee" else "Agent"),
                body=item.get("content") or "",
                origin="agent",
                created_at=_parse_at(item.get("at")),
            )
        )

    for index, item in enumerate(view.get("work_notes") or []):
        author = item.get("author") or "Agent"
        author_type = "system" if "orchestrator" in author.lower() else "agent"
        key = f"note:{index}:{author}:{item.get('note', '')}"
        db.add(
            WorkNote(
                id=_stable_id("note", ticket.id, key),
                ticket_id=ticket.id,
                author=author,
                author_type=author_type,
                body=item.get("note") or "",
                origin="agent",
                created_at=_parse_at(item.get("at")),
            )
        )

    db.flush()
