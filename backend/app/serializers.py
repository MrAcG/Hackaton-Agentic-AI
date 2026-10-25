from backend.app.models import Message, Ticket, WorkNote
from backend.app.schemas import ChatMessageOut, MutationDelta, TicketBundle, TicketOut, WorkNoteOut


def ticket_out(ticket: Ticket) -> TicketOut:
    return TicketOut.model_validate(ticket)


def message_out(message: Message) -> ChatMessageOut:
    return ChatMessageOut.model_validate(message)


def note_out(note: WorkNote) -> WorkNoteOut:
    return WorkNoteOut.model_validate(note)


def bundle(ticket: Ticket) -> TicketBundle:
    notes = sorted(ticket.work_notes, key=lambda n: n.created_at)
    messages = sorted(ticket.messages, key=lambda m: m.created_at)
    return TicketBundle(
        ticket=ticket_out(ticket),
        work_notes=[note_out(n) for n in notes],
        messages=[message_out(m) for m in messages],
    )


def delta(ticket: Ticket, notes: list[WorkNote] | None = None, messages: list[Message] | None = None) -> MutationDelta:
    return MutationDelta(
        ticket=ticket_out(ticket),
        work_notes=[note_out(n) for n in (notes or [])],
        messages=[message_out(m) for m in (messages or [])],
    )