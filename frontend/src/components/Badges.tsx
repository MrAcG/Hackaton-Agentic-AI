import type { Priority, TicketState } from "../types";

export function StateBadge({ state }: { state: TicketState }) {
  return (
    <span className="badge" data-kind="state" data-value={state}>
      {state}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: Priority }) {
  return (
    <span className="badge" data-kind="priority" data-value={priority.slice(0, 1)}>
      {priority}
    </span>
  );
}
