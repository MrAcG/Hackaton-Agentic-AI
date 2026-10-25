# Agentic Ops — AI Applications Hackathon Project Document

*Paste or export this file into Word for submission. Add team photos and the GitHub URL on the cover.*

---

## 1. Project Overview

**Project title:** Agentic Ops — Agentic AI for IT and Business Operations  

**Team members:** Aquil · Vybhavi · Divyansh  

**Problem statement:**  
Employees open many repetitive IT and operations requests (VPN failures, application access, policy questions). L1 analysts spend time classifying tickets, searching knowledge bases, chatting for basic checks, and writing resolution notes. Delay frustrates employees; specialists get interrupted by work that follows a known runbook.

**Target users:**  
- Direct: employees (callers) and IT / ops service desk analysts  
- Indirect: Network, Application, and Finance operations teams  

**Proposed solution:**  
A multi-agent platform behind a lightweight ITSM-style portal. An orchestrator classifies each ticket and routes it to a fixed specialist agent (Network, Application, or Finance). Specialists use team knowledge bases and approved tools, chat with the employee in-app (Teams stand-in), document work notes, and resolve or escalate.

**Why Agentic AI is appropriate:**  
This is not a single FAQ chatbot. Work requires **goal-directed steps**: classify → retrieve procedure → run diagnostics → ask the user → verify → close or escalate. Different departments need different tools and knowledge with clear boundaries. Agentic design (orchestrator + specialists + tools + human escalation) matches how real ITSM work is organized.

**Repository:** https://github.com/MrAcG/Hackaton-Agentic-AI  

---

## 2. Agentic AI Design

### Overall workflow

1. Employee submits an incident in the portal (or would submit via ServiceNow in production).  
2. **Orchestrator** classifies intent/team and confidence; writes a routing work note.  
3. **Specialist agent** loads that team’s KB, runs allowed tools (Network), or returns guided policy help (App/Finance stubs).  
4. If a user action is needed, the agent asks in chat and **pauses** (portal state *Pending*).  
5. Employee replies → agent resumes, verifies, then **resolves** or **escalates** to a human queue.  

### Agent responsibilities

| Agent | Responsibility |
|-------|----------------|
| Orchestrator | Classify and route; never deep-troubleshoot |
| Network | VPN/Wi-Fi/DNS/outage L1 loop with mock diagnostics |
| Application | Stub: KB guidance + hand-off to Application Support |
| Finance | Stub: policy guidance + hand-off to Finance Ops |
| Human queue | Destination for low confidence, failed fixes, outages, stubs |

### Tools / external resources

- Keyword knowledge base over `data/kb/<team>/*.md`  
- Mock network tools: site status, VPN, Wi-Fi, ping, DNS  
- FastAPI + SQLite ticket store  
- Optional LLM for richer wording/routing (`AGENT_LLM_PROVIDER`; default rules-only)  

### Context required

Ticket title/description/requester, chat history, tool results, KB hits, turn count, prior classification.

### Human-in-the-loop

- Escalation when user remediation fails, outage detected, max clarifying turns exceeded, or stub teams hand off  
- Service desk can still patch state / add work notes in the portal  
- Low-confidence routing flagged in work notes  

### Architecture

**Multi-agent, fixed specialists.** One reusable agent definition per team; **new session per ticket** (LangGraph `thread_id`), not a new agent type per ticket.

```text
Portal (Divyansh) → FastAPI (Aquil) → AgentService (Vybhavi)
                                      ├─ Orchestrator
                                      ├─ Network agent (+ tools + KB)
                                      ├─ Application stub
                                      └─ Finance stub
```

*(Insert workflow diagram from slides / Canva here.)*

---

## 3. Working Prototype

**What runs today**

- React ITSM portal (queue, create, detail, chat, work notes)  
- FastAPI `/api/tickets*` wired to LangGraph via `AgentService`  
- Network demo path with pause/resume; App/Finance stubs  
- Automated tests + HTTP scenario script  

**GitHub:** https://github.com/MrAcG/Hackaton-Agentic-AI  
If the repo is private, add collaborator **TinyZhen**.

**How to run:** see root `README.md` and `docs/DEMO.md`.

---

## 4. Demo

**Story:** Problem → User opens VPN ticket → Agentic workflow → Resolved with notes.

Follow `docs/DEMO.md`. Core value: one realistic L1 ticket handled end-to-end with visible routing, chat, and documentation — not every department equally deep.

---

## 5. Evaluation

See `docs/EVALUATION.md` for tables of expected vs actual outcomes, successes, failures, limitations, and improvements.

**Summary:** Agent unit/graph suite **32 passed**; HTTP e2e scenarios **5/5 passed** (VPN resolve, Wi-Fi escalate, outage, finance stub, application stub).

---

## 6. Project Documentation

| Topic | Location |
|-------|----------|
| Run instructions | `README.md` |
| Demo script | `docs/DEMO.md` |
| Evaluation | `docs/EVALUATION.md` |
| Agent integration | `backend/agents/README.md` |
| Portal API contract | `frontend/src/api.ts` |
| Slide / poster outlines | `docs/SLIDES_OUTLINE.md`, `docs/POSTER_OUTLINE.md` |

### Major technologies

Python, FastAPI, SQLAlchemy/SQLite, LangGraph, React, Vite, TypeScript.

### Known limitations

Mock tools/KB; no production ServiceNow/Teams; in-memory agent checkpoints; App/Finance are stubs; demo API unauthenticated.

---

## Ownership

| Person | Contribution |
|--------|----------------|
| Vybhavi | LangGraph orchestrator, Network agent, stubs, KB, agent tests |
| Divyansh | Mock ITSM portal UI |
| Aquil | FastAPI persistence, portal↔agent wiring, evaluation & packaging docs |
