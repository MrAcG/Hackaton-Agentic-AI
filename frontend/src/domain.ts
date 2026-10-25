import type {
  AssignmentGroup,
  ChatMessage,
  MutationDelta,
  NewTicketInput,
  Snapshot,
  Ticket,
  TicketPatch,
  TicketState,
  WorkNote,
} from "./types";

let counter = 0;

function uid(prefix: string): string {
  counter += 1;
  return `${prefix}-${Date.now().toString(36)}-${counter}`;
}

export function nextNumber(tickets: Ticket[]): string {
  const max = tickets.reduce((highest, ticket) => {
    const value = Number(ticket.number.replace(/^\D+/, ""));
    return Number.isFinite(value) ? Math.max(highest, value) : highest;
  }, 10000);
  return `INC${String(max + 1).padStart(7, "0")}`;
}

export function mergeSnapshot(snapshot: Snapshot, delta: MutationDelta): Snapshot {
  let tickets = snapshot.tickets;
  for (const ticket of delta.tickets ?? []) {
    const index = tickets.findIndex((item) => item.id === ticket.id);
    tickets =
      index === -1
        ? [ticket, ...tickets]
        : tickets.map((item) => (item.id === ticket.id ? ticket : item));
  }
  return {
    tickets,
    notes: [...snapshot.notes, ...(delta.notes ?? [])],
    messages: [...snapshot.messages, ...(delta.messages ?? [])],
  };
}

export function replaceBundle(
  snapshot: Snapshot,
  bundle: { ticket: Ticket; work_notes: WorkNote[]; messages: ChatMessage[] },
): Snapshot {
  const exists = snapshot.tickets.some((ticket) => ticket.id === bundle.ticket.id);
  return {
    tickets: exists
      ? snapshot.tickets.map((ticket) => (ticket.id === bundle.ticket.id ? bundle.ticket : ticket))
      : [bundle.ticket, ...snapshot.tickets],
    notes: [
      ...snapshot.notes.filter((note) => note.ticket_id !== bundle.ticket.id),
      ...bundle.work_notes,
    ],
    messages: [
      ...snapshot.messages.filter((message) => message.ticket_id !== bundle.ticket.id),
      ...bundle.messages,
    ],
  };
}

function workNote(ticketId: string, body: string, createdAt: string): WorkNote {
  return {
    id: uid("note"),
    ticket_id: ticketId,
    author: "Service desk",
    author_type: "human",
    body,
    created_at: createdAt,
  };
}

function systemMessage(ticketId: string, body: string, createdAt: string): ChatMessage {
  return {
    id: uid("msg"),
    ticket_id: ticketId,
    role: "system",
    author: "Service desk",
    body,
    created_at: createdAt,
  };
}

export function createTicketRecord(snapshot: Snapshot, input: NewTicketInput, now = new Date().toISOString()): MutationDelta {
  const number = nextNumber(snapshot.tickets);
  const ticket: Ticket = {
    id: number,
    number,
    short_description: input.short_description.trim(),
    description: input.description.trim(),
    caller: input.caller.trim(),
    caller_email: input.caller_email.trim(),
    category: input.category,
    priority: input.priority,
    state: "New",
    assignment_group: "Unassigned",
    assigned_to: "Unassigned",
    contact_type: "Self-service",
    opened_at: now,
    updated_at: now,
  };
  return {
    tickets: [ticket],
    notes: [
      {
        id: uid("note"),
        ticket_id: ticket.id,
        author: "Portal",
        author_type: "system",
        body: "Incident opened from the self-service portal.",
        created_at: now,
      },
    ],
    messages: [
      {
        id: uid("msg"),
        ticket_id: ticket.id,
        role: "employee",
        author: ticket.caller,
        body: ticket.description || ticket.short_description,
        created_at: now,
      },
    ],
  };
}

export function updateTicketRecord(
  snapshot: Snapshot,
  ticketId: string,
  patch: TicketPatch,
  now = new Date().toISOString(),
): MutationDelta | null {
  const current = snapshot.tickets.find((ticket) => ticket.id === ticketId);
  if (!current) return null;

  const next: Ticket = { ...current, updated_at: now };
  const notes: WorkNote[] = [];
  const messages: ChatMessage[] = [];
  let changed = false;

  if (patch.priority && patch.priority !== current.priority) {
    next.priority = patch.priority;
    notes.push(workNote(ticketId, `Priority changed from ${current.priority} to ${patch.priority}.`, now));
    changed = true;
  }

  if (patch.assignment_group && patch.assignment_group !== current.assignment_group) {
    const group: AssignmentGroup = patch.assignment_group;
    next.assignment_group = group;
    next.assigned_to = group === "Unassigned" ? "Unassigned" : `${group} Agent`;
    notes.push(
      workNote(
        ticketId,
        `Assignment group changed from ${current.assignment_group} to ${group}. Assigned to ${next.assigned_to}.`,
        now,
      ),
    );
    changed = true;
  }

  if (patch.state && patch.state !== current.state) {
    const state: TicketState = patch.state;
    next.state = state;
    notes.push(workNote(ticketId, `State changed from ${current.state} to ${state}.`, now));
    if (state === "Resolved") {
      messages.push(systemMessage(ticketId, "Service desk marked this incident resolved.", now));
    } else if (state === "Escalated") {
      messages.push(systemMessage(ticketId, "This incident was escalated to a human specialist.", now));
    } else if ((current.state === "Resolved" || current.state === "Closed") && state === "In Progress") {
      messages.push(systemMessage(ticketId, "This incident was reopened.", now));
    }
    changed = true;
  }

  if (!changed) return { tickets: [current] };
  return { tickets: [next], notes, messages };
}

export function addMessageRecord(
  snapshot: Snapshot,
  ticketId: string,
  body: string,
  role: "employee" | "agent",
  author: string,
  now = new Date().toISOString(),
): MutationDelta | null {
  const ticket = snapshot.tickets.find((item) => item.id === ticketId);
  const text = body.trim();
  if (!ticket || !text) return null;
  return {
    tickets: [{ ...ticket, updated_at: now }],
    messages: [
      {
        id: uid("msg"),
        ticket_id: ticketId,
        role,
        author,
        body: text,
        created_at: now,
      },
    ],
  };
}

export function addWorkNoteRecord(
  snapshot: Snapshot,
  ticketId: string,
  body: string,
  now = new Date().toISOString(),
): MutationDelta | null {
  const ticket = snapshot.tickets.find((item) => item.id === ticketId);
  const text = body.trim();
  if (!ticket || !text) return null;
  return {
    tickets: [{ ...ticket, updated_at: now }],
    notes: [workNote(ticketId, text, now)],
  };
}
