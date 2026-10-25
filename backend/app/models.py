from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # same as number, e.g. INC0010001
    number: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    short_description: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    caller: Mapped[str] = mapped_column(String(120))
    caller_email: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(64))
    priority: Mapped[str] = mapped_column(String(32))
    state: Mapped[str] = mapped_column(String(32), default="New")
    assignment_group: Mapped[str] = mapped_column(String(32), default="Unassigned")
    assigned_to: Mapped[str] = mapped_column(String(64), default="Unassigned")
    contact_type: Mapped[str] = mapped_column(String(32), default="Self-service")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    messages: Mapped[list["Message"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")
    work_notes: Mapped[list["WorkNote"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # employee | agent | system
    author: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(16), default="portal")  # portal | agent
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped["Ticket"] = relationship(back_populates="messages")


class WorkNote(Base):
    __tablename__ = "work_notes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), index=True)
    author: Mapped[str] = mapped_column(String(120))
    author_type: Mapped[str] = mapped_column(String(16))  # system | agent | human
    body: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(16), default="portal")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped["Ticket"] = relationship(back_populates="work_notes")


class IdCounter(Base):
    __tablename__ = "id_counters"

    name: Mapped[str] = mapped_column(String(32), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=10000)