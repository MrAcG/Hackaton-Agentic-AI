import { useEffect, useMemo, useState } from "react";
import {
  configuredApiBase,
  createLocalRepository,
  createRemoteRepository,
  type Repository,
} from "./api";
import { IncidentDetail } from "./components/IncidentDetail";
import { IncidentList } from "./components/IncidentList";
import { NewIncident } from "./components/NewIncident";
import { mergeSnapshot, replaceBundle } from "./domain";
import type { AssignmentGroup, MutationDelta, PortalRole, Snapshot, TicketPatch, TicketState } from "./types";
import { DEMO_CALLER, STATES } from "./types";

type Route = { name: "list" } | { name: "new" } | { name: "detail"; id: string };
type StateFilter = "All" | TicketState;
type GroupFilter = "All" | AssignmentGroup;

const ROLE_KEY = "agentic-ops.role";

function parseHash(): Route {
  const hash = window.location.hash.replace(/^#/, "");
  if (hash === "/new") return { name: "new" };
  const match = hash.match(/^\/incidents\/([^/?#]+)/);
  if (match) return { name: "detail", id: decodeURIComponent(match[1]) };
  return { name: "list" };
}

function toHash(route: Route): string {
  if (route.name === "new") return "#/new";
  if (route.name === "detail") return `#/incidents/${encodeURIComponent(route.id)}`;
  return "#/incidents";
}

function readRole(): PortalRole {
  return sessionStorage.getItem(ROLE_KEY) === "caller" ? "caller" : "desk";
}

export function App() {
  const [repo, setRepo] = useState<Repository | null>(null);
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [role, setRole] = useState<PortalRole>(readRole);
  const [route, setRoute] = useState<Route>(parseHash);
  const [source, setSource] = useState<"local" | "api">("local");
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [query, setQuery] = useState("");
  const [stateFilter, setStateFilter] = useState<StateFilter>("All");
  const [groupFilter, setGroupFilter] = useState<GroupFilter>("All");

  useEffect(() => {
    if (!window.location.hash) {
      window.history.replaceState(null, "", "#/incidents");
    }
    const onHash = () => setRoute(parseHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    let cancel = false;
    async function load() {
      const base = configuredApiBase();
      if (base) {
        const remote = createRemoteRepository(base);
        try {
          const next = await remote.load();
          if (cancel) return;
          setRepo(remote);
          setSnap(next);
          setSource("api");
          return;
        } catch {
          if (cancel) return;
          setNotice("The API did not respond. Showing the local mock.");
        }
      }
      const local = createLocalRepository();
      const next = await local.load();
      if (cancel) return;
      setRepo(local);
      setSnap(next);
      setSource("local");
    }
    void load();
    return () => {
      cancel = true;
    };
  }, []);

  useEffect(() => {
    if (!repo || repo.mode !== "remote" || route.name !== "detail") return;
    let cancel = false;
    repo
      .getTicket(route.id)
      .then((bundle) => {
        if (!cancel) setSnap((current) => (current ? replaceBundle(current, bundle) : current));
      })
      .catch((err: unknown) => {
        if (!cancel) setError(err instanceof Error ? err.message : "Could not load this incident.");
      });
    return () => {
      cancel = true;
    };
  }, [repo, route]);

  function go(next: Route) {
    const hash = toHash(next);
    if (window.location.hash === hash) {
      setRoute(parseHash());
      return;
    }
    window.location.hash = hash;
  }

  function chooseRole(next: PortalRole) {
    setRole(next);
    sessionStorage.setItem(ROLE_KEY, next);
  }

  const visible = useMemo(() => {
    if (!snap) return [];
    return snap.tickets.filter((ticket) => role === "desk" || ticket.caller === DEMO_CALLER);
  }, [snap, role]);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const state of STATES) map.set(state, 0);
    for (const ticket of visible) map.set(ticket.state, (map.get(ticket.state) ?? 0) + 1);
    return map;
  }, [visible]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return visible
      .filter((ticket) => stateFilter === "All" || ticket.state === stateFilter)
      .filter((ticket) => groupFilter === "All" || ticket.assignment_group === groupFilter)
      .filter((ticket) => {
        if (!needle) return true;
        return `${ticket.number} ${ticket.short_description} ${ticket.description} ${ticket.caller} ${ticket.category}`
          .toLowerCase()
          .includes(needle);
      })
      .sort((a, b) => b.updated_at.localeCompare(a.updated_at));
  }, [visible, query, stateFilter, groupFilter]);

  async function run(action: () => Promise<MutationDelta>): Promise<boolean> {
    setBusy(true);
    setError(null);
    try {
      const delta = await action();
      setSnap((current) => (current ? mergeSnapshot(current, delta) : current));
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function resetDemo() {
    if (!repo || repo.mode !== "local") return;
    if (!window.confirm("Reset the local mock back to the sample incidents?")) return;
    setError(null);
    try {
      const next = await repo.reset();
      setSnap(next);
      go({ name: "list" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reset the demo.");
    }
  }

  const detailTicket = route.name === "detail" && snap ? snap.tickets.find((ticket) => ticket.id === route.id) : undefined;
  const detailBlocked = Boolean(detailTicket && role === "caller" && detailTicket.caller !== DEMO_CALLER);

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => go({ name: "list" })}>
          <span className="mark" aria-hidden="true">
            AO
          </span>
          <span>
            <span className="brand-name">Agentic Ops</span>
            <span className="brand-sub">ITSM portal</span>
          </span>
        </button>
        <button
          className="nav-link"
          type="button"
          aria-current={route.name === "list" ? "page" : undefined}
          onClick={() => go({ name: "list" })}
        >
          Incidents
        </button>
        <div className="top-actions">
          {role === "caller" ? <span className="who">{DEMO_CALLER}</span> : null}
          <div className="seg" role="group" aria-label="Portal role">
            <button type="button" aria-pressed={role === "desk"} onClick={() => chooseRole("desk")}>
              Service desk
            </button>
            <button type="button" aria-pressed={role === "caller"} onClick={() => chooseRole("caller")}>
              Caller
            </button>
          </div>
          <span className="pill">{source === "api" ? "API" : "Local mock"}</span>
          {source === "local" ? (
            <button className="linkish" type="button" onClick={() => void resetDemo()}>
              Reset demo
            </button>
          ) : null}
        </div>
      </header>

      <main className="main">
        {notice ? <p className="notice">{notice}</p> : null}
        {error ? (
          <p className="alert" role="alert">
            {error}
          </p>
        ) : null}
        {role === "caller" && route.name === "list" ? (
          <p className="notice">Signed in as {DEMO_CALLER}. Internal work notes stay on the service desk record.</p>
        ) : null}
        {!snap || !repo ? (
          <p className="lede">Loading incidents…</p>
        ) : route.name === "new" ? (
          <NewIncident
            key={role}
            role={role}
            busy={busy}
            onCancel={() => go({ name: "list" })}
            onCreate={async (input) => {
              const delta = await (async () => {
                setBusy(true);
                setError(null);
                try {
                  return await repo.createTicket(input);
                } catch (err) {
                  setError(err instanceof Error ? err.message : "Could not open the incident.");
                  return null;
                } finally {
                  setBusy(false);
                }
              })();
              if (!delta) return false;
              setSnap((current) => (current ? mergeSnapshot(current, delta) : current));
              const id = delta.tickets?.[0]?.id;
              if (id) go({ name: "detail", id });
              return true;
            }}
          />
        ) : route.name === "detail" && detailBlocked ? (
          <section className="card card-pad empty">
            <h1>This incident belongs to another caller.</h1>
            <p className="lede">The caller view opens only incidents for {DEMO_CALLER}.</p>
            <button className="btn" type="button" onClick={() => go({ name: "list" })}>
              Back to incidents
            </button>
          </section>
        ) : route.name === "detail" && detailTicket ? (
          <IncidentDetail
            ticket={detailTicket}
            notes={[...snap.notes.filter((note) => note.ticket_id === detailTicket.id)].sort((a, b) =>
              b.created_at.localeCompare(a.created_at),
            )}
            messages={[...snap.messages.filter((message) => message.ticket_id === detailTicket.id)].sort((a, b) =>
              a.created_at.localeCompare(b.created_at),
            )}
            role={role}
            busy={busy}
            onBack={() => go({ name: "list" })}
            onSend={(body) =>
              run(() =>
                repo.addMessage(detailTicket.id, {
                  body,
                  role: role === "caller" ? "employee" : "agent",
                  author: role === "caller" ? DEMO_CALLER : detailTicket.assigned_to === "Unassigned" ? "Service desk" : detailTicket.assigned_to,
                }),
              )
            }
            onAddNote={(body) => run(() => repo.addWorkNote(detailTicket.id, body))}
            onPatch={(patch: TicketPatch) => run(() => repo.updateTicket(detailTicket.id, patch))}
          />
        ) : route.name === "detail" ? (
          <section className="card card-pad empty">
            <h1>No incident with that number.</h1>
            <button className="btn" type="button" onClick={() => go({ name: "list" })}>
              Back to incidents
            </button>
          </section>
        ) : (
          <IncidentList
            tickets={filtered}
            total={visible.length}
            counts={counts}
            query={query}
            stateFilter={stateFilter}
            groupFilter={groupFilter}
            onQuery={setQuery}
            onState={setStateFilter}
            onGroup={setGroupFilter}
            onClear={() => {
              setQuery("");
              setStateFilter("All");
              setGroupFilter("All");
            }}
            onOpen={(id) => go({ name: "detail", id })}
            onCreate={() => go({ name: "new" })}
          />
        )}
      </main>
    </div>
  );
}
