"""The interface the FastAPI backend calls. Nothing outside this package
needs to know about LangGraph.

    svc = AgentService()
    view = svc.start_ticket({"id": "INC001", "title": "VPN down", "description": "...", "requester": "Sam"})
    if view["awaiting_user"]:
        view = svc.send_message("INC001", "done, it works now")

Every method returns a TicketView dict (see `_view`) for the portal to render.
"""

from __future__ import annotations

from typing import Any

from .config import AgentSettings, load_settings
from .kb import KeywordKnowledgeBase, KnowledgeBase
from .llm import get_chat_model
from .orchestrator import build_graph


class TicketNotFound(KeyError):
    pass


class TicketAlreadyStarted(ValueError):
    pass


class TicketNotAwaitingUser(ValueError):
    pass


_UNSET = object()


class AgentService:
    def __init__(
        self,
        settings: AgentSettings | None = None,
        kb: KnowledgeBase | None = None,
        llm: Any = _UNSET,
        checkpointer: Any | None = None,
    ):
        self.settings = settings or load_settings()
        self.kb = kb or KeywordKnowledgeBase(self.settings.kb_dir)
        self.llm = get_chat_model(self.settings) if llm is _UNSET else llm
        self.graph = build_graph(self.settings, self.kb, self.llm, checkpointer)

    @staticmethod
    def _config(ticket_id: str) -> dict[str, Any]:
        return {"configurable": {"thread_id": str(ticket_id)}}

    def _snapshot(self, ticket_id: str):
        return self.graph.get_state(self._config(ticket_id))

    def _pending_interrupt(self, snapshot) -> Any | None:
        for task in getattr(snapshot, "tasks", ()) or ():
            for intr in getattr(task, "interrupts", ()) or ():
                return getattr(intr, "value", intr)
        return None

    def _view(self, ticket_id: str) -> dict[str, Any]:
        snapshot = self._snapshot(ticket_id)
        values = snapshot.values or {}
        if not values:
            raise TicketNotFound(ticket_id)
        question = self._pending_interrupt(snapshot)
        return {
            "ticket_id": str(ticket_id),
            "status": values.get("status", "new"),
            "team": values.get("team"),
            "classification": values.get("classification"),
            "awaiting_user": question is not None,
            "question": question.get("question") if isinstance(question, dict) else question,
            "chat": values.get("chat", []),
            "work_notes": values.get("work_notes", []),
            "findings": values.get("findings"),
            "diagnostics": values.get("diagnostics", []),
            "kb_hits": [{k: h[k] for k in ("doc_id", "title", "score")} for h in values.get("kb_hits", [])],
            "resolution": values.get("resolution"),
            "escalation": values.get("escalation"),
        }

    def start_ticket(self, ticket: dict[str, Any]) -> dict[str, Any]:
        ticket_id = ticket.get("id")
        if not ticket_id:
            raise ValueError("ticket needs an 'id'")
        if self._snapshot(ticket_id).values:
            raise TicketAlreadyStarted(ticket_id)
        initial = {"ticket": ticket, "status": "new", "chat": [], "work_notes": [], "diagnostics": [], "user_turns": 0}
        self.graph.invoke(initial, self._config(ticket_id))
        return self._view(ticket_id)

    def send_message(self, ticket_id: str, message: str) -> dict[str, Any]:
        from langgraph.types import Command

        snapshot = self._snapshot(ticket_id)
        if not snapshot.values:
            raise TicketNotFound(ticket_id)
        if self._pending_interrupt(snapshot) is None:
            raise TicketNotAwaitingUser(f"Ticket {ticket_id} is {snapshot.values.get('status')} and not waiting for a reply")
        self.graph.invoke(Command(resume=message), self._config(ticket_id))
        return self._view(ticket_id)

    def get_ticket(self, ticket_id: str) -> dict[str, Any]:
        return self._view(ticket_id)
