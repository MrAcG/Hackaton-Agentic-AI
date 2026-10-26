"""Specialist agents for non-network teams: team questions -> KB guidance -> human queue."""

from __future__ import annotations

from typing import Any

from .kb import KnowledgeBase, section
from .llm import polish
from .state import TicketState, agent_msg, note, user_msg
from .teams import TEAM_INTAKE, TEAM_LABEL, TEAM_QUEUE


class StubAgent:
    def __init__(self, team: str, kb: KnowledgeBase, llm: Any | None = None):
        if team not in TEAM_INTAKE:
            raise ValueError(f"Unknown specialist team: {team}")
        self.team = team
        self.name = f"{TEAM_LABEL[team]} Agent"
        self.kb = kb
        self.llm = llm
        self.queue = TEAM_QUEUE[team]

    def _say(self, text: str) -> dict[str, Any]:
        return agent_msg(self.name, polish(self.llm, text))

    def intake(self, state: TicketState) -> dict[str, Any]:
        ticket = state["ticket"]
        name = ticket.get("requester") or "there"
        prior = state.get("last_user_reply") or ""
        text = f"{ticket.get('title', '')}\n{ticket.get('description', '')}\n{prior}"
        hits = self.kb.search(text, team=self.team, k=2)
        question = f"Hi {name}, you've been routed to **{TEAM_LABEL[self.team]}**. {TEAM_INTAKE[self.team]}"
        message = self._say(question)
        return {
            "status": "awaiting_user",
            "kb_hits": hits,
            "pending": {"kind": "clarify", "question": message["content"]},
            "chat": [message],
            "work_notes": [
                note(
                    self.name,
                    f"Team intake started. Preliminary KB: {', '.join(h['doc_id'] for h in hits) or 'none'}.",
                )
            ],
        }

    def wait(self, state: TicketState) -> dict[str, Any]:
        from langgraph.types import interrupt

        reply = interrupt({"ticket_id": state["ticket"].get("id"), "question": (state.get("pending") or {}).get("question")})
        reply = str(reply).strip()
        return {
            "status": "in_progress",
            "last_user_reply": reply,
            "user_turns": state.get("user_turns", 0) + 1,
            "chat": [user_msg(state["ticket"].get("requester") or "Employee", reply)],
        }

    def finish(self, state: TicketState) -> dict[str, Any]:
        ticket = state["ticket"]
        name = ticket.get("requester") or "there"
        reply = state.get("last_user_reply") or ""
        # Prefer the specialist reply; triage context may still be in ticket description.
        combined = f"{ticket.get('title', '')}\n{ticket.get('description', '')}\n{reply}"
        hits = self.kb.search(combined, team=self.team, k=2)
        if hits:
            top = hits[0]
            guidance = section(top["content"], "Resolution") or top.get("snippet") or top.get("content", "")[:400]
            text = (
                f"Thanks {name}. Based on your answers, this looks closest to \"{top.get('title', top['doc_id'])}\".\n\n"
                f"Approved guidance from our {TEAM_LABEL[self.team]} knowledge base:\n{guidance}\n\n"
                f"I've also escalated this to **{self.queue}** with your details so a human can finish "
                f"anything that needs elevated access or judgment."
            )
            kb_line = ", ".join(h["doc_id"] for h in hits)
        else:
            text = (
                f"Thanks {name}. I captured your answers for the {TEAM_LABEL[self.team]} team and escalated to "
                f"**{self.queue}**. A specialist will follow up here with your context attached."
            )
            kb_line = "no matching runbooks"
        return {
            "status": "escalated",
            "kb_hits": hits,
            "pending": None,
            "escalation": {
                "to": self.queue,
                "reason": f"{TEAM_LABEL[self.team]} specialist: guidance shared after team intake; human follow-up required.",
                "suggested_runbook": hits[0]["doc_id"] if hits else None,
                "user_context": reply[:500],
            },
            "chat": [self._say(text)],
            "work_notes": [
                note(self.name, f"User context: {reply[:300] or '(empty)'}. KB: {kb_line}. Escalated to {self.queue}.")
            ],
        }
