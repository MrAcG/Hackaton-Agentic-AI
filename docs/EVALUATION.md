# Evaluation

**Team:** Aquil, Vybhavi, Divyansh  
**Prototype:** Agentic Ops (mock ITSM + LangGraph specialists)  
**Date:** October 2025

## Method

1. **Unit / graph tests** — `python -m pytest tests/agents -v` (32 tests + 13 subtests, rules-only LLM mode).
2. **HTTP end-to-end** — `python scripts/e2e_scenarios.py` against FastAPI + `AgentService` (portal contract).
3. **Manual portal demo** — create VPN ticket in UI with `VITE_API_URL` set; chat resume; confirm work notes.

## Representative cases

| ID | Input (summary) | Expected | Actual (API e2e) | Result |
|----|-----------------|----------|------------------|--------|
| E1 | VPN auth expired | Route Network → ask user → resolve after success reply | Pending → Resolved | Pass |
| E2 | Slow Wi-Fi / freezing calls | Network → ask → escalate if still broken | Pending → Escalated | Pass |
| E3 | Whole office site outage | Network → escalate immediately (no user fix) | Escalated | Pass |
| E4 | Expense reimbursement | Finance stub → guidance + escalate | Escalated (Finance) | Pass |
| E5 | Outlook crash | Application stub → guidance + escalate | Escalated (Application) | Pass |

### Agent graph tests (selected)

| Case | Expected | Actual |
|------|----------|--------|
| VPN pause/resume resolve | awaiting_user → resolved | Pass |
| Fix fails | escalated to Network L2 | Pass |
| Outage | escalated, no ask | Pass |
| Unclear connection → clarify → VPN | re-diagnose + ask | Pass |
| Finance / app stubs | KB tip + escalate | Pass |
| Ticket sessions isolated | separate thread_ids | Pass |

### Routing (classifier)

| Ticket theme | Expected team | Notes |
|--------------|---------------|--------|
| VPN / Wi-Fi / DNS | network | Pass (rules) |
| Outlook / locked account | application | Pass |
| Expense / invoice | finance | Pass |
| Vague “help” | application + low confidence | Pass (flagged) |

## Successful behaviors

- Fixed specialist agents with **one LangGraph session per ticket** (not spawn-per-ticket).
- Network agent diagnoses from **mock tool output**, not free invention of infrastructure state.
- **Interrupt / resume** chat (`ask_user` → portal Pending → employee reply).
- Orchestrator writes routing work notes; specialists append diagnosis / escalation notes.
- Portal remote mode stays in sync after agent mutations (detail refetch).

## Failure / edge cases observed

| Case | Behavior | Mitigation |
|------|----------|------------|
| LLM returns invalid JSON | Falls back to keyword rules | Built-in |
| User reply unclear | Ask again; escalate after max turns | `AGENT_MAX_USER_TURNS` (default 3) |
| Vague ticket text | Default route + low confidence flag | Human review in work notes |
| App/Finance depth | Stub only (KB + hand-off) | Intentional MVP scope |
| API down | Portal falls back to localStorage mock | No live agents in mock mode |

## Limitations

- Mock diagnostics and keyword KB (not production monitoring or vector RAG).
- No real ServiceNow / Microsoft Teams / Entra ID.
- In-memory agent checkpointer (sessions reset when API process restarts).
- Application and Finance agents do not run multi-step tool loops.
- No authentication on the demo API.

## Possible improvements

1. Persist LangGraph checkpoints (SQLite/Postgres) across restarts.
2. Optional embeddings RAG behind the existing `KnowledgeBase` interface.
3. Deepen Application (identity workflows with HITL) as a second demo path.
4. Short polling or SSE so the portal updates without refetch on every action.
5. Structured evaluation dashboard (routing accuracy %, time-to-resolve vs baseline).

## How to reproduce

```powershell
pip install -r requirements.txt
python -m pytest tests/agents -v
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
python scripts\e2e_scenarios.py
```
