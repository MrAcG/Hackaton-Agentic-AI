# Agentic Ops — Agentic AI for IT & Business Operations

Hackathon prototype that routes employee support tickets to specialist AI agents, troubleshoots with team knowledge bases, chats in-app, and documents outcomes in a mock ITSM portal.

## About the application

Everyday IT and ops requests (VPN failures, MFA loops, laptop issues, Outlook crashes, expense questions, phishing reports, HR onboarding) burn L1 time on the same classify → ask → runbook → close loop.

**Agentic Ops** models that work as a multi-agent system:

1. An employee opens an incident in the portal (no category picker — the AI decides).
2. A **triage orchestrator** asks clarifying questions, then assigns a specialist team.
3. That team’s agent asks follow-ups grounded in its runbooks (`data/kb/<team>/`).
4. **Network** can run mock diagnostics, guide a fix, verify, and resolve.
5. Other teams share KB guidance and escalate to a human queue when elevated access or judgment is needed.
6. Chat, assignment group, state, and work notes stay visible in the portal.

### Support teams

| Team | Focus |
|------|--------|
| Network | VPN, Wi-Fi, DNS, connectivity (deep demo path + tools) |
| Endpoint | Laptop / desktop / printer / hardware |
| Identity | Password, MFA, SSO, account lock, access |
| Application | Business apps (NetSuite, Salesforce, etc.) |
| Collaboration | Outlook, Teams, email, SharePoint, meetings |
| Security | Phishing, malware, suspicious activity |
| Finance | Expenses, invoices, reimbursements, POs |
| HR Ops | Onboarding, benefits, PTO, people ops |

This is a **mock** ITSM stack (not production ServiceNow or Microsoft Teams). Sensitive actions escalate to humans; agents do not collect real passwords.

## Prerequisites

- Python 3.11+ (3.12–3.14 also work)
- Node.js 18+ and npm
- Optional: an OpenAI API key for natural-language routing and polished replies (works without one via keyword rules)

## How to run

Clone or open this repository, then use two terminals from the **project root**.

### 1. Backend (API + agents)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` if you want live LLM behavior:

```env
AGENT_LLM_PROVIDER=openai
AGENT_LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
```

For offline / free demos, set `AGENT_LLM_PROVIDER=none` (rules-only routing and replies).

Start the API:

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: http://127.0.0.1:8000/health  
- OpenAPI docs: http://127.0.0.1:8000/docs  

### 2. Frontend (portal)

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open http://localhost:5173 — the status pill should show **API** when the backend is reachable.

Without `VITE_API_URL`, the portal falls back to an in-browser localStorage mock (no live agents).

### 3. Quick try in the UI

1. Role: **Caller** → **New incident**
2. Short description + description of the problem (e.g. VPN auth failed)
3. Submit → open the ticket
4. Answer the **Orchestrator** triage questions in chat
5. Answer the specialist’s follow-ups
6. Watch state move to **Resolved** or **Escalated**, with work notes updated

### 4. Agents CLI (optional)

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/agents -v
python -m backend.agents.demo --scenario vpn_auth_expired --notes
python scripts\e2e_scenarios.py   # API must already be on :8000
```

## Ticket flow

```text
Portal → FastAPI → AgentService (LangGraph)
  START → Orchestrator intake (ask) → classify
       → Network (tools + KB + verify)  OR
       → Endpoint / Identity / Application / Collaboration /
         Security / Finance / HR Ops (team questions + KB → escalate)
```

1. `POST /api/tickets` — save ticket, start agent session  
2. Orchestrator asks triage questions (portal state **Pending**)  
3. Employee reply → classify → assign team  
4. Specialist asks team-specific questions / runs Network tools  
5. Resolve or escalate; chat + work notes sync back to the portal  

## Project layout

```text
backend/app/       # FastAPI + SQLite ITSM API
backend/agents/    # LangGraph orchestrator + specialist agents
frontend/          # React / Vite mock ITSM portal
data/kb/           # Markdown runbooks per team
docs/              # Demo script, evaluation, deliverable outlines
scripts/           # smoke_api.py, e2e_scenarios.py
tests/agents/      # Unit + graph tests
```

## Further docs

| Doc | Purpose |
|-----|---------|
| [docs/DEMO.md](docs/DEMO.md) | Live demo script |
| [docs/EVALUATION.md](docs/EVALUATION.md) | Test cases and limitations |
| [docs/PROJECT_DOCUMENT.md](docs/PROJECT_DOCUMENT.md) | Hackathon project write-up |
| [docs/SLIDES_OUTLINE.md](docs/SLIDES_OUTLINE.md) | Slide outline (build in Canva/Slides — no AI slide tools) |
| [docs/POSTER_OUTLINE.md](docs/POSTER_OUTLINE.md) | Poster outline |
| [backend/agents/README.md](backend/agents/README.md) | Agent integration details |

## Known limitations

- Network is the only deep tool-using path; other teams are intake + KB + human hand-off stubs.
- Agent session checkpoints are in-memory (API restart drops mid-chat sessions).
- Mock diagnostics and KB only — not connected to real ServiceNow, AD, or VPN gear.
- Demo API is unauthenticated and local-only.
