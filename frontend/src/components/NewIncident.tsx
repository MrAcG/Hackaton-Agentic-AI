import { useState, type FormEvent } from "react";
import type { NewTicketInput, PortalRole, Priority } from "../types";
import { DEMO_CALLER, DEMO_EMAIL, PRIORITIES, isPriority } from "../types";

interface NewIncidentProps {
  role: PortalRole;
  busy: boolean;
  onCancel: () => void;
  onCreate: (input: NewTicketInput) => Promise<boolean>;
}

export function NewIncident({ role, busy, onCancel, onCreate }: NewIncidentProps) {
  const [caller, setCaller] = useState(role === "caller" ? DEMO_CALLER : "");
  const [email, setEmail] = useState(role === "caller" ? DEMO_EMAIL : "");
  const [priority, setPriority] = useState<Priority>("3 - Moderate");
  const [shortDescription, setShortDescription] = useState("");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!caller.trim() || !email.trim()) {
      setFormError("Caller name and email are required.");
      return;
    }
    if (!shortDescription.trim()) {
      setFormError("Short description is required.");
      return;
    }
    if (!description.trim()) {
      setFormError("Description is required.");
      return;
    }
    setFormError(null);
    await onCreate({
      caller: caller.trim(),
      caller_email: email.trim(),
      priority,
      short_description: shortDescription.trim(),
      description: description.trim(),
    });
  }

  return (
    <section>
      <button className="btn back" type="button" onClick={onCancel}>
        Back to incidents
      </button>
      <div className="page-head">
        <div>
          <h1>New incident</h1>
          <p className="lede">
            Describe the problem. Triage AI asks a few questions, then routes you to the right specialist team
            (Network, Endpoint, Identity, Application, Collaboration, Security, Finance, or HR Ops).
          </p>
        </div>
      </div>
      <form className="card card-pad form-grid" onSubmit={(event) => void submit(event)}>
        <label>
          Caller
          <input
            value={caller}
            readOnly={role === "caller"}
            onChange={(event) => setCaller(event.target.value)}
            autoComplete="name"
          />
        </label>
        <label>
          Email
          <input
            type="email"
            value={email}
            readOnly={role === "caller"}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
          />
        </label>
        <label className="span-2">
          Priority
          <select
            value={priority}
            onChange={(event) => {
              if (isPriority(event.target.value)) setPriority(event.target.value);
            }}
          >
            {PRIORITIES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label className="span-2">
          Short description
          <input
            value={shortDescription}
            onChange={(event) => setShortDescription(event.target.value)}
            autoFocus
            required
            placeholder="e.g. VPN keeps failing when I work from home"
          />
        </label>
        <label className="span-2">
          Description
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            required
            placeholder="What happens, any error text, when it started…"
          />
        </label>
        {formError ? (
          <p className="form-error span-2" role="alert">
            {formError}
          </p>
        ) : null}
        <div className="actions span-2">
          <button className="btn primary" type="submit" disabled={busy}>
            Open incident
          </button>
          <button className="btn" type="button" onClick={onCancel}>
            Cancel
          </button>
        </div>
      </form>
    </section>
  );
}
