import type { AgentSnapshot } from "../types";

interface AgentActivityProps {
  agent: AgentSnapshot | null | undefined;
  loading?: boolean;
}

export function AgentActivity({ agent, loading }: AgentActivityProps) {
  if (loading && !agent) {
    return (
      <article className="card card-pad agent-panel">
        <h2>Agent activity</h2>
        <p className="hint">Loading specialist session…</p>
      </article>
    );
  }

  if (!agent) {
    return (
      <article className="card card-pad agent-panel">
        <h2>Agent activity</h2>
        <p className="hint">No live agent session for this incident yet.</p>
      </article>
    );
  }

  const classification = agent.classification;
  const findings = agent.findings;
  const diagnostics = agent.diagnostics ?? [];
  const kbHits = agent.kb_hits ?? [];
  const waiting = Boolean(agent.awaiting_user);

  return (
    <article className="card card-pad agent-panel">
      <div className="agent-panel-head">
        <h2>Agent activity</h2>
        <span className={`agent-pill ${waiting ? "wait" : agent.status}`}>{waiting ? "Waiting on you" : agent.status}</span>
      </div>
      <p className="hint">
        This is the multi-agent trail: orchestrator routing, tools the specialist ran, and what it still needs from you.
      </p>

      {waiting && agent.question ? (
        <div className="agent-banner">
          <strong>Agent needs your reply</strong>
          <p>{agent.question}</p>
        </div>
      ) : null}

      <div className="agent-grid">
        <div>
          <span className="agent-label">Specialist</span>
          <p>{agent.team ? `${agent.team} agent` : "Unassigned"}</p>
        </div>
        <div>
          <span className="agent-label">Session</span>
          <p>{agent.ticket_id}</p>
        </div>
      </div>

      {classification ? (
        <div className="agent-block">
          <span className="agent-label">Orchestrator routing</span>
          <p>
            <strong>{classification.team}</strong> · confidence {Math.round((classification.confidence ?? 0) * 100)}% ·{" "}
            {classification.method}
          </p>
          <p className="muted">{classification.reason}</p>
        </div>
      ) : null}

      {findings?.root_cause ? (
        <div className="agent-block">
          <span className="agent-label">Working diagnosis</span>
          <p>
            <strong>{findings.root_cause}</strong>
          </p>
          {findings.evidence ? <p className="muted">{findings.evidence}</p> : null}
        </div>
      ) : null}

      {diagnostics.length > 0 ? (
        <div className="agent-block">
          <span className="agent-label">Diagnostics run</span>
          <ul className="agent-tools">
            {diagnostics.map((item, index) => (
              <li key={`${item.tool}-${item.run ?? index}-${index}`}>
                <code>
                  {item.tool}
                  {item.run != null ? ` · run ${item.run}` : ""}
                </code>
                <span>{formatOutput(item.output)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="agent-block">
          <span className="agent-label">Diagnostics run</span>
          <p className="muted">None yet — agent is interviewing you before probing.</p>
        </div>
      )}

      {kbHits.length > 0 ? (
        <div className="agent-block">
          <span className="agent-label">Knowledge used</span>
          <ul className="agent-tools">
            {kbHits.map((hit) => (
              <li key={hit.doc_id}>
                <code>{hit.doc_id}</code>
                <span>
                  {hit.title}
                  {hit.score != null ? ` · score ${hit.score}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {agent.resolution ? (
        <div className="agent-block ok">
          <span className="agent-label">Resolution</span>
          <p>{agent.resolution}</p>
        </div>
      ) : null}

      {agent.escalation ? (
        <div className="agent-block warn">
          <span className="agent-label">Escalation</span>
          <p>
            <strong>{agent.escalation.to}</strong> — {agent.escalation.reason}
          </p>
        </div>
      ) : null}
    </article>
  );
}

function formatOutput(output: unknown): string {
  if (!output || typeof output !== "object") return String(output ?? "");
  try {
    return JSON.stringify(output);
  } catch {
    return String(output);
  }
}
