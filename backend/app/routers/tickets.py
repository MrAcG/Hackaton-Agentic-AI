from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.agents.service import TicketAlreadyStarted, TicketNotAwaitingUser, TicketNotFound
from backend.app.agents_bridge import get_agent_service
from backend.app.database import get_db
from backend.app.ids import next_incident_number
from backend.app.mapping import apply_agent_view
from backend.app.models import Message, Ticket, WorkNote, utcnow
from backend.app.schemas import (
    MessageCreate,
    MutationDelta,
    NewTicketInput,
    TicketBundle,
    TicketOut,
    TicketPatch,
    WorkNoteCreate,
    WorkNoteOut,
    ChatMessageOut,
)
from backend.app.serializers import bundle, delta, message_out, note_out, ticket_out

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _get_ticket(db: Session, ticket_id: str) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Incident not found.")
    return ticket


@router.get("", response_model=list[TicketOut])
def list_tickets(db: Session = Depends(get_db)) -> list[Ticket]:
    return db.query(Ticket).order_by(Ticket.opened_at.desc()).all()


@router.post("", response_model=MutationDelta, status_code=status.HTTP_201_CREATED)
def create_ticket(payload: NewTicketInput, db: Session = Depends(get_db)) -> MutationDelta:
    number = next_incident_number(db)
    now = utcnow()
    ticket = Ticket(
        id=number,
        number=number,
        short_description=payload.short_description.strip(),
        description=payload.description.strip(),
        caller=payload.caller.strip(),
        caller_email=payload.caller_email.strip(),
        category=payload.category or "Other",
        priority=payload.priority,
        state="New",
        assignment_group="Unassigned",
        assigned_to="Unassigned",
        contact_type="Self-service",
        opened_at=now,
        updated_at=now,
    )
    db.add(ticket)

    opened = WorkNote(
        id=_uid("note"),
        ticket_id=number,
        author="Portal",
        author_type="system",
        body="Incident opened from the self-service portal.",
        origin="portal",
        created_at=now,
    )
    opening_chat = Message(
        id=_uid("msg"),
        ticket_id=number,
        role="employee",
        author=payload.caller.strip() or "Employee",
        body=payload.description.strip(),
        origin="portal",
        created_at=now,
    )
    db.add(opened)
    db.add(opening_chat)
    db.flush()

    agents = get_agent_service()
    new_notes = [opened]
    new_messages = [opening_chat]
    try:
        view = agents.start_ticket(
            {
                "id": number,
                "title": ticket.short_description,
                "description": ticket.description,
                "requester": ticket.caller,
                "priority": ticket.priority,
                # No caller category — orchestrator AI classifies from title/description.
            }
        )
        apply_agent_view(db, ticket, view)
        db.flush()
        db.refresh(ticket)
        new_notes = [n for n in ticket.work_notes]
        # Portal opening message + agent-synced chat
        new_messages = [m for m in ticket.messages]
    except TicketAlreadyStarted:
        pass
    except Exception as exc:  # keep ticket even if agents fail
        db.add(
            WorkNote(
                id=_uid("note"),
                ticket_id=number,
                author="System",
                author_type="system",
                body=f"Agent orchestration failed: {exc}",
                origin="portal",
                created_at=utcnow(),
            )
        )
        db.flush()
        db.refresh(ticket)
        new_notes = list(ticket.work_notes)
        new_messages = list(ticket.messages)

    db.commit()
    db.refresh(ticket)
    return delta(ticket, notes=new_notes, messages=new_messages)


@router.get("/{ticket_id}", response_model=TicketBundle)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> TicketBundle:
    return bundle(_get_ticket(db, ticket_id))


@router.patch("/{ticket_id}", response_model=MutationDelta)
def patch_ticket(ticket_id: str, payload: TicketPatch, db: Session = Depends(get_db)) -> MutationDelta:
    ticket = _get_ticket(db, ticket_id)
    data = payload.model_dump(exclude_unset=True)
    notes: list[WorkNote] = []
    messages: list[Message] = []
    now = utcnow()

    if "state" in data and data["state"] != ticket.state:
        old = ticket.state
        ticket.state = data["state"]
        body = f"State changed from {old} to {ticket.state}."
        if ticket.state == "Resolved":
            body = "Incident marked Resolved by the service desk."
            messages.append(
                Message(
                    id=_uid("msg"),
                    ticket_id=ticket.id,
                    role="system",
                    author="Service desk",
                    body="Your incident was marked Resolved. Reply here if you still need help.",
                    origin="portal",
                    created_at=now,
                )
            )
        elif ticket.state == "Escalated":
            body = "Incident escalated to a human queue."
            messages.append(
                Message(
                    id=_uid("msg"),
                    ticket_id=ticket.id,
                    role="system",
                    author="Service desk",
                    body="Your incident was escalated to a specialist. Someone will follow up shortly.",
                    origin="portal",
                    created_at=now,
                )
            )
        note = WorkNote(
            id=_uid("note"),
            ticket_id=ticket.id,
            author="Service desk",
            author_type="human",
            body=body,
            origin="portal",
            created_at=now,
        )
        notes.append(note)
        db.add(note)
        for message in messages:
            db.add(message)

    if "assignment_group" in data:
        ticket.assignment_group = data["assignment_group"]
    if "priority" in data:
        ticket.priority = data["priority"]

    ticket.updated_at = now
    db.commit()
    db.refresh(ticket)
    return delta(ticket, notes=notes, messages=messages)


@router.post("/{ticket_id}/messages", response_model=MutationDelta)
def post_message(ticket_id: str, payload: MessageCreate, db: Session = Depends(get_db)) -> MutationDelta:
    ticket = _get_ticket(db, ticket_id)
    now = utcnow()
    agents = get_agent_service()

    # Employee replies that the agent is waiting on go through AgentService;
    # the TicketView rebuilds chat (including the user turn).
    if payload.role == "employee":
        try:
            view = agents.get_ticket(ticket_id)
            if view.get("awaiting_user"):
                view = agents.send_message(ticket_id, payload.body)
                apply_agent_view(db, ticket, view)
                ticket.updated_at = now
                db.commit()
                db.refresh(ticket)
                return MutationDelta(
                    ticket=ticket_out(ticket),
                    work_notes=[note_out(n) for n in sorted(ticket.work_notes, key=lambda x: x.created_at)],
                    messages=[message_out(m) for m in sorted(ticket.messages, key=lambda x: x.created_at)],
                )
        except TicketNotFound:
            pass
        except TicketNotAwaitingUser:
            pass
        except Exception as exc:
            note = WorkNote(
                id=_uid("note"),
                ticket_id=ticket.id,
                author="System",
                author_type="system",
                body=f"Agent resume failed: {exc}",
                origin="portal",
                created_at=now,
            )
            db.add(note)

    message = Message(
        id=_uid("msg"),
        ticket_id=ticket.id,
        role=payload.role,
        author=payload.author,
        body=payload.body.strip(),
        origin="portal",
        created_at=now,
    )
    db.add(message)
    ticket.updated_at = now
    db.commit()
    db.refresh(message)
    db.refresh(ticket)
    return MutationDelta(ticket=ticket_out(ticket), messages=[message_out(message)])


@router.post("/{ticket_id}/work-notes", response_model=WorkNoteOut)
def post_work_note(ticket_id: str, payload: WorkNoteCreate, db: Session = Depends(get_db)) -> WorkNote:
    ticket = _get_ticket(db, ticket_id)
    note = WorkNote(
        id=_uid("note"),
        ticket_id=ticket.id,
        author=payload.author,
        author_type="human",
        body=payload.body.strip(),
        origin="portal",
        created_at=utcnow(),
    )
    db.add(note)
    ticket.updated_at = utcnow()
    db.commit()
    db.refresh(note)
    return note


@router.get("/{ticket_id}/agent")
def get_agent_view(ticket_id: str, db: Session = Depends(get_db)):
    _get_ticket(db, ticket_id)
    try:
        return get_agent_service().get_ticket(ticket_id)
    except TicketNotFound as exc:
        raise HTTPException(status_code=404, detail="Agent session not found for this ticket.") from exc