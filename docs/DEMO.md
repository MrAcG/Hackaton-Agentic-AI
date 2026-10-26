# Live demo script (3–7 minutes)

**Goal:** Show triage → Network VPN resolve end-to-end, then briefly show another team (Identity / Finance / Collaboration).

## Before you start

Terminal 1 — API (from project root):

```powershell
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
Everyday tickets — VPN failures, MFA loops, Outlook crashes, expense questions — burn L1 time on repetitive runbooks and back-and-forth chat.

### 2. Solution (40–50s)
**Agentic Ops:** a mock ITSM portal plus fixed specialist agents across eight real-org teams. A triage orchestrator asks clarifying questions, then routes to the right team AI. Specialists use team knowledge and (for Network) approved mock tools. Sensitive work escalates to humans.

### 3. Live path — VPN (90–120s)
1. Role: **Caller** → **New incident** (no category picker)
2. Short description: `VPN authentication failed`  
   Description: `My VPN says authentication expired and I cannot get on the corporate network.`
3. Submit → open the incident
4. Show: Orchestrator triage questions (Pending). Reply with something like:  
   `Network / VPN from home — GlobalProtect auth expired`
5. Show: assignment **Network**, specialist follow-up (MFA / reconnect)
6. Reply: `I re-authenticated with MFA and it works now`
7. Show: state **Resolved**, work notes with diagnosis + verification (switch to **Service desk** if needed)

### 4. Optional second ticket (30s)
Open an MFA lockout, expense reimbursement, or Outlook crash ticket. Answer triage toward Identity / Finance / Collaboration to show team-specific questions and **Escalated** hand-off.

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
