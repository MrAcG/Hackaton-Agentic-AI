from __future__ import annotations

from typing import Any

from backend.agents.service import TicketNotFound
from backend.app.agents_bridge import get_agent_service
from backend.app.models import Message, Ticket, WorkNote
from backend.app.schemas import ChatMessageOut, MutationDelta, TicketBundle, TicketOut, WorkNoteOut


def ticket_out(ticket: Ticket) -> TicketOut:
    return TicketOut.model_validate(ticket)


def message_out(message: Message) -> ChatMessageOut:
    return ChatMessageOut.model_validate(message)


def note_out(note: WorkNote) -> WorkNoteOut:
    return WorkNoteOut.model_validate(note)


def agent_snapshot(ticket_id: str) -> dict[str, Any] | None:
    try:
        return get_agent_service().get_ticket(ticket_id)
    except TicketNotFound:
        return None
    except Exception:
        return None


def bundle(ticket: Ticket) -> TicketBundle:
    notes = sorted(ticket.work_notes, key=lambda n: n.created_at)
    messages = sorted(ticket.messages, key=lambda m: m.created_at)
    return TicketBundle(
        ticket=ticket_out(ticket),
        work_notes=[note_out(n) for n in notes],
        messages=[message_out(m) for m in messages],
        agent=agent_snapshot(ticket.id),
    )


def delta(
    ticket: Ticket,
    notes: list[WorkNote] | None = None,
    messages: list[Message] | None = None,
    include_agent: bool = True,
) -> MutationDelta:
    payload = MutationDelta(
        ticket=ticket_out(ticket),
        work_notes=[note_out(n) for n in (notes or [])],
        messages=[message_out(m) for m in (messages or [])],
    )
    return payload
