# Agents (LangGraph)

Orchestrator triage → eight specialist teams (Network deep path + stubs), chat pause/resume.

## Run it

```bash
pip install -r backend/requirements-agents.txt
# or: pip install -r requirements.txt from the repo root
python -m pytest tests/agents -v
python -m backend.agents.demo --scenario vpn_auth_expired --notes
```

Demo scenarios: `vpn_auth_expired`, `weak_wifi`, `dns_failure`, `site_outage`, `healthy`.  
Without `--scenario` you type your own ticket.

## How it works

```
START -> orchestrator_intake -> wait (interrupt) -> classify
   |-> network_triage -> analyze -> ask/verify/resolve|escalate
   |-> endpoint|identity|application|collaboration|security|finance|hr
         *_intake -> wait -> finish (KB guidance + human queue)
```

- **Fixed agents, one session per ticket.** Every ticket is a LangGraph thread (`thread_id = ticket id`) with a checkpointer, so a ticket can pause while waiting for the employee and resume later.
- **Orchestrator intake** asks which area the issue is in before routing; answers are folded into classification.
- **Classifier** (`classifier.py` + `teams.py`) routes with an LLM when configured, otherwise weighted keywords across 8 teams. Low-confidence routes are flagged in the work notes.
- **Network agent** (`network_agent.py`) interviews like L1 when the ticket is vague, then reads KB runbooks and runs mock diagnostics, diagnosing **from tool output only**:
  - vague / unknown → clarify-first questions;
  - user-fixable cause (VPN token, DNS cache, weak Wi-Fi) → sends the fix, waits, **re-runs checks to verify**, resolves with a written summary;
  - site outage → escalates immediately with the incident number;
  - still stuck → escalates after `AGENT_MAX_USER_TURNS` (default 3).
- **Other team stubs** ask that team's intake questions, share matching KB guidance, then escalate to the human queue.
- **Mock tools** (`tools/network_tools.py`): site status, VPN status, Wi-Fi signal, ping, DNS.
- **KB** (`kb.py`): keyword search over `data/kb/<team>/*.md`.

## Backend integration

Only `AgentService` is needed; LangGraph stays inside this package.

```python
from backend.agents.service import AgentService, TicketNotFound, TicketAlreadyStarted, TicketNotAwaitingUser

agents = AgentService()

@app.post("/tickets")
def create(t: TicketIn):
    return agents.start_ticket({"id": t.id, "title": t.title, "description": t.description, "requester": t.requester})

@app.post("/tickets/{tid}/messages")
def reply(tid: str, body: MessageIn):
    return agents.send_message(tid, body.text)

@app.get("/tickets/{tid}/agent")
def view(tid: str):
    return agents.get_ticket(tid)
```

### TicketView (what the portal renders)

| field | type | notes |
|---|---|---|
| `status` | `new \| in_progress \| awaiting_user \| resolved \| escalated` | |
| `team` | `network \| endpoint \| identity \| application \| collaboration \| security \| finance \| hr` | |
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
# in .env at repo root
AGENT_LLM_PROVIDER=openai   # or anthropic; "none" = rules only
OPENAI_API_KEY=...
AGENT_LLM_MODEL=gpt-4o      # optional override
```

With an LLM: smarter routing, reply interpretation, and friendlier wording. Every LLM call falls back to rules on error. Tests always run without one.
