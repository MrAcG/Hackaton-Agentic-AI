import { useEffect, useRef, useState } from "react";
import type { ChatMessage, PortalRole, Ticket, TicketPatch, WorkNote } from "../types";
import { GROUPS, PRIORITIES, STATES, isGroup, isPriority, isState } from "../types";
import { formatWhen } from "../format";
import { PriorityBadge, StateBadge } from "./Badges";

interface IncidentDetailProps {
  ticket: Ticket;
  notes: WorkNote[];
  messages: ChatMessage[];
  role: PortalRole;
  busy: boolean;
  onBack: () => void;
  onSend: (body: string) => Promise<boolean>;
  onAddNote: (body: string) => Promise<boolean>;
  onPatch: (patch: TicketPatch) => Promise<boolean>;
}

export function IncidentDetail({
  ticket,
  notes,
  messages,
  role,
  busy,
  onBack,
  onSend,
  onAddNote,
  onPatch,
}: IncidentDetailProps) {
  const [draft, setDraft] = useState("");
  const [note, setNote] = useState("");
  const [chatError, setChatError] = useState<string | null>(null);
  const [noteError, setNoteError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const desk = role === "desk";
  const replyAuthor = ticket.assigned_to === "Unassigned" ? "Service desk" : ticket.assigned_to;

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  async function send() {
    if (!draft.trim()) {
      setChatError("Write a message before sending.");
      return;
    }
    setChatError(null);
    const ok = await onSend(draft);
    if (ok) setDraft("");
  }

  async function saveNote() {
    if (!note.trim()) {
      setNoteError("Write a work note before saving.");
      return;
    }
    setNoteError(null);
    const ok = await onAddNote(note);
    if (ok) setNote("");
  }

  return (
    <section>
      <button className="btn back" type="button" onClick={onBack}>
        Back to incidents
      </button>
      <div className="head-row">
        <div>
          <p className="eyebrow">{ticket.number}</p>
          <h1>{ticket.short_description}</h1>
          <div className="meta-row">
            <StateBadge state={ticket.state} />
            <PriorityBadge priority={ticket.priority} />
            <span className="muted">{ticket.assignment_group}</span>
            <span className="muted">{ticket.caller}</span>
          </div>
          {ticket.id === "INC0010042" && ticket.state === "In Progress" ? (
            <p className="demo-line">Waiting on the caller to refresh the Corp-VPN certificate.</p>
          ) : null}
        </div>
        {desk ? (
          <div className="actions">
            {ticket.state === "Resolved" || ticket.state === "Closed" ? (
              <button className="btn primary" type="button" disabled={busy} onClick={() => void onPatch({ state: "In Progress" })}>
                Reopen
              </button>
            ) : (
              <button className="btn primary" type="button" disabled={busy} onClick={() => void onPatch({ state: "Resolved" })}>
                Resolve
              </button>
            )}
            <button
              className="btn warn"
              type="button"
              disabled={busy || ticket.state === "Escalated"}
              onClick={() => void onPatch({ state: "Escalated" })}
            >
              Escalate
            </button>
          </div>
        ) : null}
      </div>

      <div className="detail-grid">
        <div className="stack">
          <article className="card card-pad">
            <h2>Record</h2>
            <div className="fields">
              <Field label="Caller" value={ticket.caller} />
              <Field label="Email" value={ticket.caller_email} />
              <Field label="Category" value={ticket.category} />
              <Field label="Contact type" value={ticket.contact_type} />
              <Field label="Opened" value={formatWhen(ticket.opened_at)} />
              <Field label="Updated" value={formatWhen(ticket.updated_at)} />
              <Field label="Assigned to" value={ticket.assigned_to} />
              {desk ? (
                <>
                  <label>
                    State
                    <select
                      value={ticket.state}
                      disabled={busy}
                      onChange={(event) => {
                        if (isState(event.target.value)) void onPatch({ state: event.target.value });
                      }}
                    >
                      {STATES.map((state) => (
                        <option key={state} value={state}>
                          {state}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Assignment group
                    <select
                      value={ticket.assignment_group}
                      disabled={busy}
                      onChange={(event) => {
                        if (isGroup(event.target.value)) void onPatch({ assignment_group: event.target.value });
                      }}
                    >
                      {GROUPS.map((group) => (
                        <option key={group} value={group}>
                          {group}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Priority
                    <select
                      value={ticket.priority}
                      disabled={busy}
                      onChange={(event) => {
                        if (isPriority(event.target.value)) void onPatch({ priority: event.target.value });
                      }}
                    >
                      {PRIORITIES.map((priority) => (
                        <option key={priority} value={priority}>
                          {priority}
                        </option>
                      ))}
                    </select>
                  </label>
                </>
              ) : (
                <Field label="Priority" value={ticket.priority} />
              )}
            </div>
            <div className="prose">
              <span>Description</span>
              <p>{ticket.description}</p>
            </div>
          </article>

          {desk ? (
            <article className="card card-pad">
              <h2>Work notes</h2>
              <p className="hint">Internal. The caller does not see these notes.</p>
              {notes.length === 0 ? <p className="hint">No work notes yet.</p> : null}
              <div>
                {notes.map((item) => (
                  <article key={item.id} className="note">
                    <div className="note-meta">
                      <strong>{item.author}</strong>
                      <span className="kind">{item.author_type}</span>
                      <span>{formatWhen(item.created_at)}</span>
                    </div>
                    <p>{item.body}</p>
                  </article>
                ))}
              </div>
              <div className="composer">
                <label>
                  Add a work note
                  <textarea
                    value={note}
                    onChange={(event) => setNote(event.target.value)}
                    placeholder="Diagnosis, evidence, and the next step."
                  />
                </label>
                <button className="btn" type="button" disabled={busy} onClick={() => void saveNote()}>
                  Add work note
                </button>
                {noteError ? (
                  <p className="form-error" role="alert">
                    {noteError}
                  </p>
                ) : null}
              </div>
            </article>
          ) : null}
        </div>

        <aside className="card card-pad chat-card">
          <h2>Employee chat</h2>
          <p className="hint">
            {desk ? "Visible to the caller. This stands in for Teams." : "Messages with the support agent."}
          </p>
          <div className="chat-log" aria-live="polite">
            {messages.length === 0 ? <p className="hint">No messages yet.</p> : null}
            {messages.map((item) => {
              const mine = desk ? item.role === "agent" : item.role === "employee";
              return (
                <div key={item.id} className={`bubble ${item.role === "system" ? "system" : mine ? "mine" : "theirs"}`}>
                  {item.role === "system" ? (
                    <p>{item.body}</p>
                  ) : (
                    <>
                      <span className="meta">
                        {item.author} · {formatWhen(item.created_at)}
                      </span>
                      <p>{item.body}</p>
                    </>
                  )}
                </div>
              );
            })}
            <div ref={endRef} />
          </div>
          <div className="composer">
            <label>
              {desk ? `Reply as ${replyAuthor}` : "Message the support agent"}
              <textarea
                value={draft}
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
                    event.preventDefault();
                    void send();
                  }
                }}
                placeholder={desk ? "This reply is visible to the caller." : "Describe what you tried and what happened."}
              />
            </label>
            <div className="composer-row">
              <span className="hint">Ctrl+Enter to send</span>
              <button className="btn primary" type="button" disabled={busy} onClick={() => void send()}>
                {desk ? "Send reply" : "Send"}
              </button>
            </div>
          </div>
          {chatError ? (
            <p className="form-error" role="alert">
              {chatError}
            </p>
          ) : null}
        </aside>
      </div>
    </section>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="field">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
