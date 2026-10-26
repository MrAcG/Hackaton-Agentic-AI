"""Quick smoke test for FastAPI + AgentService wiring."""

from __future__ import annotations

import json
import sys

import httpx

BASE = "http://127.0.0.1:8000"


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=60.0)
    health = client.get("/health")
    health.raise_for_status()
    print("health", health.json())

    created = client.post(
        "/api/tickets",
        json={
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "priority": "2 - High",
            "short_description": "VPN authentication failed",
            "description": "My VPN says authentication expired and I cannot get on the corporate network.",
        },
    )
    print("create", created.status_code)
    if created.status_code >= 400:
        print(created.text)
        return 1
    body = created.json()
    ticket = body["ticket"]
    tid = ticket["id"]
    print("ticket", tid, ticket["state"], ticket["assignment_group"])
    print("notes", len(body.get("work_notes", [])), "messages", len(body.get("messages", [])))
    for m in body.get("messages", [])[:5]:
        print(f"  [{m['role']}] {m['author']}: {m['body'][:100]}")

    detail = client.get(f"/api/tickets/{tid}")
    detail.raise_for_status()
    d = detail.json()
    print("detail state", d["ticket"]["state"], "msgs", len(d["messages"]))

    agent = client.get(f"/api/tickets/{tid}/agent")
    print("agent", agent.status_code, json.dumps({k: agent.json().get(k) for k in ("status", "awaiting_user", "team")}, indent=2) if agent.status_code == 200 else agent.text)

    if agent.status_code == 200 and agent.json().get("awaiting_user"):
        reply = client.post(
            f"/api/tickets/{tid}/messages",
            json={"body": "I re-authenticated and it works now", "role": "employee", "author": "Alex Rivera"},
        )
        print("reply", reply.status_code)
        if reply.status_code >= 400:
            print(reply.text)
            return 1
        r = reply.json()
        print("after reply", r["ticket"]["state"], "msgs", len(r.get("messages", [])))

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())