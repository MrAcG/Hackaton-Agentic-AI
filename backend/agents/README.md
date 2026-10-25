# Agents (LangGraph)

Owner: Vybhavi. Orchestrator, Network agent, Application/Finance stubs, chat pause/resume.

## Run it

```bash
pip install -r backend/requirements-agents.txt
python -m pytest tests/agents -v                         # 40 tests
python -m backend.agents.demo --scenario vpn_auth_expired --notes
```

Demo scenarios: `vpn_auth_expired`, `weak_wifi`, `dns_failure`, `site_outage`, `healthy`.
Without `--scenario` you type your own ticket.

## How it works

```
START -> classify (orchestrator) --> network_triage -> network_analyze --+--> network_ask_user -> network_wait_user (interrupt)
                                 |                         ^           |                                   |
                                 |                         |           |                         network_handle_reply
                                 |              network_rediagnose <---+------- new info ----------------- |
                                 |                                     |                                   |-- "it works" --> network_verify -> network_resolve -> END
                                 |                                     +--> network_escalate -> END <------+-- "still broken" / out of turns
                                 +--> application_agent -> END   (KB guidance + hand-off to Application Support)
                                 +--> finance_agent     -> END   (KB guidance + hand-off to Finance Ops)
```

- **Fixed agents, one session per ticket.** Every ticket is a LangGraph thread (`thread_id = ticket id`) with a checkpointer, so a ticket can pause while waiting for the employee and resume later.
- **Orchestrator** (`classifier.py`) routes with an LLM when configured, otherwise weighted keywords. Low-confidence routes are flagged in the work notes.
- **Network agent** (`network_agent.py`) reads KB runbooks, runs targeted mock diagnostics (and a full sweep if those are inconclusive), diagnoses **from tool output only**, then:
  - user-fixable cause (VPN token, DNS cache, weak Wi-Fi) → sends the fix, waits, **re-runs checks to verify**, resolves;
  - site outage → escalates immediately with the incident number;
  - nothing found → asks the employee for details, re-diagnoses, and escalates after `AGENT_MAX_USER_TURNS` (default 3).
- **Mock tools** (`tools/network_tools.py`): site status, VPN status, Wi-Fi signal, ping, DNS. Their output is driven by a hidden scenario (from the ticket text, or `ticket["mock_scenario"]` to force one for a demo).
- **KB** (`kb.py`): keyword search over `data/kb/<team>/*.md`. Any object with `search(query, team, k)` can replace it (e.g. the RAG retriever).

## Backend integration (Aquil)

Only `AgentService` is needed; LangGraph stays inside this package.

```python
from backend.agents.service import AgentService, TicketNotFound, TicketAlreadyStarted, TicketNotAwaitingUser

agents = AgentService()                      # one instance for the app
# optional: AgentService(kb=my_rag_retriever, checkpointer=SqliteSaver(...))

@app.post("/tickets")                        # after saving the ticket
def create(t: TicketIn):
    return agents.start_ticket({"id": t.id, "title": t.title, "description": t.description, "requester": t.requester})

@app.post("/tickets/{tid}/messages")
def reply(tid: str, body: MessageIn):
    return agents.send_message(tid, body.text)   # 409 on TicketNotAwaitingUser, 404 on TicketNotFound

@app.get("/tickets/{tid}/agent")
def view(tid: str):
    return agents.get_ticket(tid)
```

Calls are synchronous; wrap them in `run_in_threadpool` from async routes if the LLM is enabled.

### TicketView (what the portal renders — Divyansh)

| field | type | notes |
|---|---|---|
| `status` | `new \| in_progress \| awaiting_user \| resolved \| escalated` | |
| `team` | `network \| application \| finance` | |
| `awaiting_user` / `question` | bool / str | show the reply box when true |
| `chat` | `[{role: agent\|user, author, content, at}]` | chat panel |
| `work_notes` | `[{author, note, at}]` | ITSM work notes |
| `classification` | `{team, confidence, reason, method}` | |
| `findings` | `{root_cause, evidence}` | network only |
| `diagnostics` | `[{tool, args, output, run}]` | network only |
| `kb_hits` | `[{doc_id, title, score}]` | |
| `resolution` / `escalation` | str / `{to, reason, ...}` | set when closed |

## LLM (optional)

```bash
export AGENT_LLM_PROVIDER=anthropic   # or openai; default "none" = rules only
export ANTHROPIC_API_KEY=...          # pip install langchain-anthropic
export AGENT_LLM_MODEL=...            # optional override
```

With an LLM: smarter routing, reply interpretation, and friendlier message wording. Every LLM call falls back to the rules on error, so the demo never breaks. Tests always run without one.
