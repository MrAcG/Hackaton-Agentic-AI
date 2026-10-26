# Evaluation

**Prototype:** Agentic Ops (mock ITSM + LangGraph specialists)  

## Method

1. **Unit / graph tests** — `python -m pytest tests/agents -v` (rules-only LLM mode).
2. **HTTP end-to-end** — `python scripts/e2e_scenarios.py` against FastAPI + `AgentService`.
3. **Manual portal demo** — create a ticket in the UI with `VITE_API_URL` set; answer triage; confirm specialist chat and work notes.

## Representative cases

| ID | Input (summary) | Expected | Actual (API e2e) | Result |
|----|-----------------|----------|------------------|--------|
| E1 | VPN auth expired | Triage → Network → ask user → resolve | Pending → Resolved | Pass |
| E2 | Expense reimbursement | Triage → Finance → guidance + escalate | Escalated (Finance) | Pass |
| E3 | MFA / account locked | Triage → Identity → escalate | Escalated (Identity) | Pass |
| E4 | Outlook crash | Triage → Collaboration → escalate | Escalated (Collaboration) | Pass |

### Agent graph tests (selected)

| Case | Expected | Actual |
|------|----------|--------|
| VPN pause/resume resolve | triage → awaiting_user → resolved | Pass |
| Fix fails | escalated to Network L2 | Pass |
| Outage | escalated after triage, no user fix | Pass |
| Unclear connection → clarify → VPN | re-diagnose + ask | Pass |
| Finance / Identity stubs | KB tip + escalate | Pass |
| Ticket sessions isolated | separate thread_ids | Pass |

### Routing (classifier)

| Ticket theme | Expected team | Notes |
|--------------|---------------|--------|
| VPN / Wi-Fi / DNS | network | Pass (rules) |
| Laptop / printer / boot | endpoint | Pass |
| Password / MFA / locked | identity | Pass |
| NetSuite / Salesforce | application | Pass |
| Outlook / Teams / email | collaboration | Pass |
| Phishing / malware | security | Pass |
| Expense / invoice | finance | Pass |
| Onboarding / benefits / PTO | hr | Pass |

## Successes

- Triage-before-route matches how a real service desk intake works.
- Network path demonstrates full agentic loop: diagnose → ask → verify → resolve.
- Team-scoped KB keeps guidance bounded.
- LLM optional with automatic rules fallback when the API is unavailable.

## Failures / gaps

- Non-Network teams do not run tools; they intake, cite KB, and escalate.
- In-memory LangGraph checkpoints: API restart loses mid-ticket agent state.
- Keyword routing can misfire on vague tickets when no LLM is configured.

## Limitations

Mock ITSM only; no real AD/VPN/email systems; unauthenticated local API; demo data only.

## Improvements

Persist agent checkpoints; deepen 1–2 more teams (e.g. Identity + Collaboration); add confidence UI in the portal; authenticated multi-user sessions.
