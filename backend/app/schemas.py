from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TicketState = Literal["New", "In Progress", "Pending", "Resolved", "Escalated", "Closed"]
Priority = Literal["1 - Critical", "2 - High", "3 - Moderate", "4 - Low"]
AssignmentGroup = Literal["Unassigned", "Network", "Application", "Finance"]
Category = Literal[
    "Network / Connectivity",
    "Application / NetSuite",
    "Finance / Policy",
    "Other",
]
MessageRole = Literal["employee", "agent", "system"]
AuthorType = Literal["system", "agent", "human"]


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    number: str
    short_description: str
    description: str
    caller: str
    caller_email: str
    category: str
    priority: str
    state: str
    assignment_group: str
    assigned_to: str
    contact_type: str
    opened_at: datetime
    updated_at: datetime


class WorkNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    author: str
    author_type: str
    body: str
    created_at: datetime


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    ticket_id: str
    role: str
    author: str
    body: str
    created_at: datetime


class NewTicketInput(BaseModel):
    caller: str
    caller_email: str
    category: Category
    priority: Priority
    short_description: str = Field(min_length=1)
    description: str = Field(min_length=1)


class TicketPatch(BaseModel):
    state: TicketState | None = None
    assignment_group: AssignmentGroup | None = None
    priority: Priority | None = None


class MessageCreate(BaseModel):
    body: str = Field(min_length=1)
    role: MessageRole
    author: str


class WorkNoteCreate(BaseModel):
    body: str = Field(min_length=1)
    author: str = "Service desk"


class TicketBundle(BaseModel):
    ticket: TicketOut
    work_notes: list[WorkNoteOut]
    messages: list[ChatMessageOut]


class MutationDelta(BaseModel):
    ticket: TicketOut
    work_notes: list[WorkNoteOut] = []
    messages: list[ChatMessageOut] = []