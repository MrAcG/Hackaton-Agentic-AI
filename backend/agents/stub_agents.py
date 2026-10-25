"""Application and Finance agents (MVP stubs).

They look up their team's runbooks, share the documented guidance with the
employee, and hand the ticket to the human team queue. Swap in a full flow
like NetworkAgent later without touching the orchestrator.
"""

from __future__ import annotations

from typing import Any

from .kb import KnowledgeBase, section
from .llm import polish
from .state import TicketState, agent_msg, note

QUEUES = {"application": "Application Support", "finance": "Finance Ops"}


class StubAgent:
    def __init__(self, team: str, kb: KnowledgeBase, llm: Any | None = None):
        self.team = team
        self.name = f"{team.capitalize()} Agent"
        self.kb = kb
        self.llm = llm

    def __call__(self, state: TicketState) -> dict[str, Any]:
        ticket = state["ticket"]
        name = ticket.get("requester") or "there"
        hits = self.kb.search(f"{ticket.get('title', '')}\n{ticket.get('description', '')}", team=self.team, k=2)
        queue = QUEUES[self.team]
        if hits:
            top = hits[0]
            guidance = section(top["content"], "Resolution") or top["snippet"]
            text = (
                f"Hi {name}, this looks like \"{top['title']}\". Here's what usually fixes it:\n\n{guidance}\n\n"
                f"I've also passed your ticket to the {queue} team so someone can follow up if this doesn't help."
            )
            kb_line = ", ".join(h["doc_id"] for h in hits)
        else:
            text = f"Hi {name}, I've passed your ticket to the {queue} team. They'll follow up here."
            kb_line = "no matching runbooks"
        return {
            "status": "escalated",
            "kb_hits": hits,
            "escalation": {"to": queue, "reason": "MVP stub agent: KB guidance shared, human follow-up required.", "suggested_runbook": hits[0]["doc_id"] if hits else None},
            "chat": [agent_msg(self.name, polish(self.llm, text))],
            "work_notes": [note(self.name, f"KB consulted: {kb_line}. Guidance shared with user; routed to {queue} queue.")],
        }
