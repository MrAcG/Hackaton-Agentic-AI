export const STATES = ["New", "In Progress", "Pending", "Resolved", "Escalated", "Closed"] as const;
export type TicketState = (typeof STATES)[number];

export const PRIORITIES = ["1 - Critical", "2 - High", "3 - Moderate", "4 - Low"] as const;
export type Priority = (typeof PRIORITIES)[number];

export const GROUPS = [
  "Unassigned",
  "Network",
  "Endpoint",
  "Identity",
  "Application",
  "Collaboration",
  "Security",
  "Finance",
  "HR Ops",
] as const;
export type AssignmentGroup = (typeof GROUPS)[number];

export const CATEGORIES = [
  "Other",
  "Network / Connectivity",
  "Endpoint / Hardware",
  "Identity & Access",
  "Business Applications",
  "Email & Collaboration",
  "Security",
  "Finance / Policy",
  "HR / People",
] as const;
export type Category = (typeof CATEGORIES)[number];

export type PortalRole = "desk" | "caller";

export interface Ticket {
  id: string;
  number: string;
  short_description: string;
  description: string;
  caller: string;
  caller_email: string;
  category: Category;
  priority: Priority;
  state: TicketState;
  assignment_group: AssignmentGroup;
  assigned_to: string;
  contact_type: "Self-service";
  opened_at: string;
  updated_at: string;
}

export interface WorkNote {
  id: string;
  ticket_id: string;
  author: string;
  author_type: "system" | "agent" | "human";
  body: string;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  ticket_id: string;
  role: "employee" | "agent" | "system";
  author: string;
  body: string;
  created_at: string;
}

export interface Snapshot {
  tickets: Ticket[];
  notes: WorkNote[];
  messages: ChatMessage[];
}

export interface NewTicketInput {
  caller: string;
  caller_email: string;
  priority: Priority;
  short_description: string;
  description: string;
  /** Optional; omitted so the orchestrator AI categorizes from the text. */
  category?: Category;
}

export type TicketPatch = Partial<Pick<Ticket, "state" | "assignment_group" | "priority">>;

export interface MutationDelta {
  tickets?: Ticket[];
  notes?: WorkNote[];
  messages?: ChatMessage[];
}

export interface AgentSnapshot {
  ticket_id: string;
  status: string;
  team?: string | null;
  awaiting_user?: boolean;
  question?: string | null;
  classification?: {
    team?: string;
    confidence?: number;
    reason?: string;
    method?: string;
  } | null;
  findings?: {
    root_cause?: string;
    evidence?: string;
    incident?: string;
  } | null;
  diagnostics?: Array<{ tool: string; args?: unknown; output?: unknown; run?: number }>;
  kb_hits?: Array<{ doc_id: string; title?: string; score?: number }>;
  resolution?: string | null;
  escalation?: { to?: string; reason?: string; [key: string]: unknown } | null;
  chat?: unknown[];
  work_notes?: unknown[];
}

export interface TicketBundle {
  ticket: Ticket;
  work_notes: WorkNote[];
  messages: ChatMessage[];
  agent?: AgentSnapshot | null;
}

export const DEMO_CALLER = "Alex Rivera";
export const DEMO_EMAIL = "alex.rivera@company.example";

export function isState(value: string): value is TicketState {
  return (STATES as readonly string[]).includes(value);
}

export function isPriority(value: string): value is Priority {
  return (PRIORITIES as readonly string[]).includes(value);
}

export function isGroup(value: string): value is AssignmentGroup {
  return (GROUPS as readonly string[]).includes(value);
}

export function isCategory(value: string): value is Category {
  return (CATEGORIES as readonly string[]).includes(value);
}
