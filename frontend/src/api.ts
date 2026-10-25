/**
 * ITSM API contract for the FastAPI backend.
 *
 * Leave VITE_API_URL unset to use the browser mock.
 * Set VITE_API_URL=http://localhost:8000 to use the API below.
 *
 * GET    /api/tickets
 *        -> Ticket[]
 * POST   /api/tickets
 *        body: NewTicketInput
 *        -> { ticket, work_notes, messages }
 * GET    /api/tickets/:id
 *        -> { ticket, work_notes, messages }
 * PATCH  /api/tickets/:id
 *        body: { state?, assignment_group?, priority? }
 *        -> { ticket, work_notes, messages }
 *        work_notes and messages are only the records created by this patch.
 * POST   /api/tickets/:id/messages
 *        body: { body, role: "employee" | "agent", author }
 *        -> ChatMessage
 * POST   /api/tickets/:id/work-notes
 *        body: { body, author }
 *        -> WorkNote
 *
 * A bare Ticket, ChatMessage, or WorkNote is also accepted as a response.
 */

import {
  addMessageRecord,
  addWorkNoteRecord,
  createTicketRecord,
  mergeSnapshot,
  updateTicketRecord,
} from "./domain";
import { buildSeed } from "./seed";
import type {
  ChatMessage,
  MutationDelta,
  NewTicketInput,
  Snapshot,
  Ticket,
  TicketBundle,
  TicketPatch,
  WorkNote,
} from "./types";

const STORAGE_KEY = "agentic-ops.itsm.v1";

export interface Repository {
  mode: "local" | "remote";
  load(): Promise<Snapshot>;
  reset(): Promise<Snapshot>;
  getTicket(id: string): Promise<TicketBundle>;
  createTicket(input: NewTicketInput): Promise<MutationDelta>;
  addMessage(
    ticketId: string,
    input: { body: string; role: "employee" | "agent"; author: string },
  ): Promise<MutationDelta>;
  addWorkNote(ticketId: string, body: string): Promise<MutationDelta>;
  updateTicket(ticketId: string, patch: TicketPatch): Promise<MutationDelta>;
}

export function configuredApiBase(): string {
  return (import.meta.env.VITE_API_URL ?? "").trim().replace(/\/$/, "");
}

function isSnapshot(value: unknown): value is Snapshot {
  if (!value || typeof value !== "object") return false;
  const record = value as Snapshot;
  return Array.isArray(record.tickets) && Array.isArray(record.notes) && Array.isArray(record.messages);
}

function readLocal(): Snapshot {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return writeLocal(buildSeed());
    const parsed: unknown = JSON.parse(raw);
    if (!isSnapshot(parsed)) return writeLocal(buildSeed());
    return parsed;
  } catch {
    return buildSeed();
  }
}

function writeLocal(snapshot: Snapshot): Snapshot {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
  } catch {
    // Keep the in-memory copy if storage is unavailable.
  }
  return snapshot;
}

function applyLocal(delta: MutationDelta): MutationDelta {
  writeLocal(mergeSnapshot(readLocal(), delta));
  return delta;
}

export function createLocalRepository(): Repository {
  return {
    mode: "local",
    async load() {
      return readLocal();
    },
    async reset() {
      return writeLocal(buildSeed());
    },
    async getTicket(id) {
      const snapshot = readLocal();
      const ticket = snapshot.tickets.find((item) => item.id === id);
      if (!ticket) throw new Error("Incident not found.");
      return {
        ticket,
        work_notes: snapshot.notes.filter((note) => note.ticket_id === id),
        messages: snapshot.messages.filter((message) => message.ticket_id === id),
      };
    },
    async createTicket(input) {
      return applyLocal(createTicketRecord(readLocal(), input));
    },
    async addMessage(ticketId, input) {
      const delta = addMessageRecord(readLocal(), ticketId, input.body, input.role, input.author);
      if (!delta) throw new Error("Incident not found.");
      return applyLocal(delta);
    },
    async addWorkNote(ticketId, body) {
      const delta = addWorkNoteRecord(readLocal(), ticketId, body);
      if (!delta) throw new Error("Incident not found.");
      return applyLocal(delta);
    },
    async updateTicket(ticketId, patch) {
      const delta = updateTicketRecord(readLocal(), ticketId, patch);
      if (!delta) throw new Error("Incident not found.");
      return applyLocal(delta);
    },
  };
}

function asDelta(body: unknown): MutationDelta {
  if (!body || typeof body !== "object") return {};
  const record = body as Record<string, unknown>;
  if (record.ticket && typeof record.ticket === "object") {
    return {
      tickets: [record.ticket as Ticket],
      notes: Array.isArray(record.work_notes) ? (record.work_notes as WorkNote[]) : [],
      messages: Array.isArray(record.messages) ? (record.messages as ChatMessage[]) : [],
    };
  }
  if (typeof record.number === "string" && typeof record.short_description === "string") {
    return { tickets: [record as unknown as Ticket] };
  }
  if (typeof record.role === "string" && typeof record.body === "string" && typeof record.ticket_id === "string") {
    return { messages: [record as unknown as ChatMessage] };
  }
  if (typeof record.author === "string" && typeof record.body === "string" && typeof record.ticket_id === "string") {
    return { notes: [record as unknown as WorkNote] };
  }
  return {};
}

function parseSnapshot(body: unknown): Snapshot {
  if (Array.isArray(body)) {
    return { tickets: body as Ticket[], notes: [], messages: [] };
  }
  if (isSnapshot(body)) return body;
  return { tickets: [], notes: [], messages: [] };
}

export function createRemoteRepository(baseUrl: string): Repository {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...(init?.headers ?? {}),
      },
    });
    const text = await response.text();
    if (!response.ok) {
      throw new Error((text || `Request failed (${response.status})`).slice(0, 180));
    }
    if (!text) return {} as T;
    try {
      return JSON.parse(text) as T;
    } catch {
      throw new Error("The API returned a response that was not JSON.");
    }
  }

  return {
    mode: "remote",
    async load() {
      return parseSnapshot(await request<unknown>("/api/tickets"));
    },
    async reset() {
      throw new Error("Reset is available for the local mock.");
    },
    async getTicket(id) {
      return request<TicketBundle>(`/api/tickets/${encodeURIComponent(id)}`);
    },
    async createTicket(input) {
      return asDelta(
        await request("/api/tickets", {
          method: "POST",
          body: JSON.stringify(input),
        }),
      );
    },
    async addMessage(ticketId, input) {
      return asDelta(
        await request(`/api/tickets/${encodeURIComponent(ticketId)}/messages`, {
          method: "POST",
          body: JSON.stringify(input),
        }),
      );
    },
    async addWorkNote(ticketId, body) {
      return asDelta(
        await request(`/api/tickets/${encodeURIComponent(ticketId)}/work-notes`, {
          method: "POST",
          body: JSON.stringify({ body, author: "Service desk" }),
        }),
      );
    },
    async updateTicket(ticketId, patch) {
      return asDelta(
        await request(`/api/tickets/${encodeURIComponent(ticketId)}`, {
          method: "PATCH",
          body: JSON.stringify(patch),
        }),
      );
    },
  };
}
