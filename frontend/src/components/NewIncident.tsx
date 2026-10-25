import { useState, type FormEvent } from "react";
import type { Category, NewTicketInput, PortalRole, Priority } from "../types";
import { CATEGORIES, DEMO_CALLER, DEMO_EMAIL, PRIORITIES, isCategory, isPriority } from "../types";

interface NewIncidentProps {
  role: PortalRole;
  busy: boolean;
  onCancel: () => void;
  onCreate: (input: NewTicketInput) => Promise<boolean>;
}

export function NewIncident({ role, busy, onCancel, onCreate }: NewIncidentProps) {
  const [caller, setCaller] = useState(role === "caller" ? DEMO_CALLER : "");
  const [email, setEmail] = useState(role === "caller" ? DEMO_EMAIL : "");
  const [category, setCategory] = useState<Category>("Network / Connectivity");
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
      category,
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
          <p className="lede">New incidents stay unassigned until an agent routes them.</p>
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
        <label>
          Category
          <select
            value={category}
            onChange={(event) => {
              if (isCategory(event.target.value)) setCategory(event.target.value);
            }}
          >
            {CATEGORIES.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
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
          />
        </label>
        <label className="span-2">
          Description
          <textarea value={description} onChange={(event) => setDescription(event.target.value)} required />
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
