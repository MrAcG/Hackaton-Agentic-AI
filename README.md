# Agentic AI for IT and Business Operations

Hackathon prototype: route employee tickets to specialized AI agents, troubleshoot with org knowledge, chat in-app, and document resolution in a mock ITSM portal.

**Team:** Aquil · Vybhavi · Divyansh  
**Repo:** https://github.com/MrAcG/Hackaton-Agentic-AI

| Person | Focus |
|--------|--------|
| **Vybhavi** | LangGraph agents (`backend/agents`) |
| **Divyansh** | Mock ITSM portal (`frontend`) |
| **Aquil** | FastAPI glue (`backend/app`) — persistence + wire portal ↔ agents |

## Run the full stack

### 1. Backend (API + agents)

```powershell
cd C:\Users\gonsa\Downloads\Hackaton
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: http://127.0.0.1:8000/health  
- Docs: http://127.0.0.1:8000/docs  

### 2. Frontend (portal)

```powershell
cd frontend
copy .env.example .env   # then set VITE_API_URL=http://127.0.0.1:8000
npm install
npm run dev
```

Open http://localhost:5173 — pill should show **API** when the backend is up.

Without `VITE_API_URL`, the portal uses the localStorage mock only.

### 3. Agents only (CLI)

```powershell
pip install -r backend/requirements-agents.txt
python -m pytest tests/agents -v
python -m backend.agents.demo --scenario vpn_auth_expired --notes
```

## How a ticket flows

1. Caller opens an incident in the portal → `POST /api/tickets`
2. FastAPI saves the ticket and calls `AgentService.start_ticket`
3. Orchestrator routes to Network / Application / Finance
4. Network agent may ask the employee (portal state **Pending**)
5. Employee replies in chat → `POST /api/tickets/{id}/messages` → `AgentService.send_message`
6. Ticket resolves or escalates; work notes and chat update in the portal

## Demo & evaluation

| Doc | Purpose |
|-----|---------|
| [docs/DEMO.md](docs/DEMO.md) | Live demo script (portal + API) |
| [docs/EVALUATION.md](docs/EVALUATION.md) | Test cases, results, limitations |
| [docs/PROJECT_DOCUMENT.md](docs/PROJECT_DOCUMENT.md) | Hackathon Word-doc content |
| [docs/SLIDES_OUTLINE.md](docs/SLIDES_OUTLINE.md) | 7-min slide content (build in Canva/Slides — no AI slide tools) |
| [docs/POSTER_OUTLINE.md](docs/POSTER_OUTLINE.md) | One-slide poster content |

```powershell
python -m pytest tests/agents -v
python scripts\e2e_scenarios.py   # API must be running on :8000
```

## Layout

```
backend/app/       # FastAPI (Aquil)
backend/agents/    # LangGraph (Vybhavi)
frontend/          # ITSM portal (Divyansh)
data/kb/           # Team runbooks
docs/              # Demo, evaluation, deliverable outlines
scripts/           # smoke_api.py, e2e_scenarios.py
tests/agents/      # Agent unit + graph tests
```
