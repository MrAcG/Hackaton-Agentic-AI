export const STATES = ["New", "In Progress", "Pending", "Resolved", "Escalated", "Closed"] as const;
export type TicketState = (typeof STATES)[number];

export const PRIORITIES = ["1 - Critical", "2 - High", "3 - Moderate", "4 - Low"] as const;
export type Priority = (typeof PRIORITIES)[number];

export const GROUPS = ["Unassigned", "Network", "Application", "Finance"] as const;
export type AssignmentGroup = (typeof GROUPS)[number];

export const CATEGORIES = [
  "Network / Connectivity",
  "Application / NetSuite",
  "Finance / Policy",
  "Other",
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
  category: Category;
  priority: Priority;
  short_description: string;
  description: string;
}

export type TicketPatch = Partial<Pick<Ticket, "state" | "assignment_group" | "priority">>;

export interface MutationDelta {
  tickets?: Ticket[];
  notes?: WorkNote[];
  messages?: ChatMessage[];
}

export interface TicketBundle {
  ticket: Ticket;
  work_notes: WorkNote[];
  messages: ChatMessage[];
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
