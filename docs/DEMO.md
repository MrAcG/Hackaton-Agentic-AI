# Live demo script (3–7 minutes)

**Goal:** Show one Network VPN ticket from open → agent chat → resolve, then briefly mention routing to other teams.

## Before you start

Terminal 1 — API:

```powershell
cd C:\Users\gonsa\Downloads\Hackaton
.\.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Terminal 2 — portal:

```powershell
cd frontend
npm run dev
```

Confirm http://localhost:5173 shows the **API** pill (not Local mock).

Optional CLI rehearsal (no UI):

```powershell
python -m backend.agents.demo --scenario vpn_auth_expired --notes
python scripts\e2e_scenarios.py
```

## Demo narrative

### 1. Problem (30–40s)
Everyday tickets — VPN failures, app access, expense questions — burn L1 time on repetitive runbooks and back-and-forth chat.

### 2. Solution (40–50s)
**Agentic Ops:** a mock ITSM portal plus fixed specialist agents (Network, Application, Finance). An orchestrator routes each ticket; specialists use team knowledge and approved mock tools. Sensitive work escalates to humans.

### 3. Live path — VPN (90–120s)
1. Role: **Caller** (Alex Rivera) → **New incident**
2. Category: Network / Connectivity  
   Short description: `VPN authentication failed`  
   Description: `My VPN says authentication expired and I cannot get on the corporate network.`
3. Submit → open the incident
4. Show: assignment **Network**, state **Pending**, agent chat asking for MFA / reconnect
5. Reply in chat: `I re-authenticated with MFA and it works now`
6. Show: state **Resolved**, work notes with diagnosis + verification (switch to **Service desk** role if needed)

### 4. Optional second ticket (30s)
Open a finance or “whole office outage” ticket to show **Escalated** / stub specialists without deep tooling.

### 5. Privacy / responsible AI (20–30s)
Least-privilege team KB, read-only mock diagnostics, escalate when user fix fails or confidence is low. No real credentials in chat.

### 6. Close (15s)
Faster L1 for common issues; humans stay in the loop for sensitive or hard cases.

## Status map (portal ↔ agents)

| Portal state | Agent status |
|--------------|--------------|
| New | new |
| In Progress | in_progress |
| Pending | awaiting_user |
| Resolved | resolved |
| Escalated | escalated |
