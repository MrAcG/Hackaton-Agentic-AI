import type { AssignmentGroup, Ticket, TicketState } from "../types";
import { GROUPS, STATES } from "../types";
import { formatWhen } from "../format";
import { PriorityBadge, StateBadge } from "./Badges";

type StateFilter = "All" | TicketState;
type GroupFilter = "All" | AssignmentGroup;

interface IncidentListProps {
  tickets: Ticket[];
  total: number;
  counts: Map<string, number>;
  query: string;
  stateFilter: StateFilter;
  groupFilter: GroupFilter;
  onQuery: (value: string) => void;
  onState: (value: StateFilter) => void;
  onGroup: (value: GroupFilter) => void;
  onClear: () => void;
  onOpen: (id: string) => void;
  onCreate: () => void;
}

export function IncidentList({
  tickets,
  total,
  counts,
  query,
  stateFilter,
  groupFilter,
  onQuery,
  onState,
  onGroup,
  onClear,
  onOpen,
  onCreate,
}: IncidentListProps) {
  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Incidents</h1>
          <p className="lede">
            Employee requests, the chat on each incident, and the internal notes agents leave on the record.
          </p>
        </div>
        <div className="head-tools">
          <input
            className="search"
            aria-label="Search incidents"
            placeholder="Search incidents"
            value={query}
            onChange={(event) => onQuery(event.target.value)}
          />
          <button className="btn primary" type="button" onClick={onCreate}>
            New incident
          </button>
        </div>
      </div>

      <div className="filters">
        <button className="chip" type="button" aria-pressed={stateFilter === "All"} onClick={() => onState("All")}>
          All <span>{total}</span>
        </button>
        {STATES.map((state) => (
          <button
            key={state}
            className="chip"
            type="button"
            aria-pressed={stateFilter === state}
            onClick={() => onState(state)}
          >
            {state} <span>{counts.get(state) ?? 0}</span>
          </button>
        ))}
        <label className="inline">
          Group
          <select
            value={groupFilter}
            onChange={(event) => {
              const value = event.target.value;
              onGroup(value === "All" || GROUPS.includes(value as AssignmentGroup) ? (value as GroupFilter) : "All");
            }}
          >
            <option value="All">All groups</option>
            {GROUPS.map((group) => (
              <option key={group} value={group}>
                {group}
              </option>
            ))}
          </select>
        </label>
      </div>

      {tickets.length === 0 ? (
        <div className="card empty">
          <p>No incidents match these filters.</p>
          <button className="btn" type="button" onClick={onClear}>
            Clear filters
          </button>
        </div>
      ) : (
        <div className="card table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Number</th>
                <th scope="col">Short description</th>
                <th scope="col">Caller</th>
                <th scope="col">Priority</th>
                <th scope="col">State</th>
                <th scope="col">Group</th>
                <th scope="col">Updated</th>
              </tr>
            </thead>
            <tbody>
              {tickets.map((ticket) => (
                <tr
                  key={ticket.id}
                  role="link"
                  aria-label={`${ticket.number}: ${ticket.short_description}`}
                  tabIndex={0}
                  onClick={() => onOpen(ticket.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onOpen(ticket.id);
                    }
                  }}
                >
                  <td className="mono">{ticket.number}</td>
                  <td className="clip">{ticket.short_description}</td>
                  <td className="nowrap">{ticket.caller}</td>
                  <td>
                    <PriorityBadge priority={ticket.priority} />
                  </td>
                  <td>
                    <StateBadge state={ticket.state} />
                  </td>
                  <td>{ticket.assignment_group}</td>
                  <td className="muted nowrap">{formatWhen(ticket.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
