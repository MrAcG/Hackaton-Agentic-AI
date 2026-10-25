"""Sprint B — exercise portal API ↔ AgentService scenarios end-to-end."""

from __future__ import annotations

import sys

import httpx

BASE = "http://127.0.0.1:8000"

CASES = [
    {
        "name": "vpn_resolve",
        "ticket": {
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "category": "Network / Connectivity",
            "priority": "2 - High",
            "short_description": "VPN authentication failed",
            "description": "My VPN says authentication expired and I cannot get on the corporate network.",
        },
        "expect_team": "Network",
        "expect_after_create": "Pending",
        "reply": "I re-authenticated with MFA and it works now",
        "expect_final": "Resolved",
    },
    {
        "name": "wifi_escalate",
        "ticket": {
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "category": "Network / Connectivity",
            "priority": "3 - Moderate",
            "short_description": "Office Wi-Fi is very slow",
            "description": "Wi-Fi is slow and my video calls keep freezing on the corp network.",
        },
        "expect_team": "Network",
        "expect_after_create": "Pending",
        "reply": "No, still slow after moving closer to the AP",
        "expect_final": "Escalated",
    },
    {
        "name": "site_outage",
        "ticket": {
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "category": "Network / Connectivity",
            "priority": "1 - Critical",
            "short_description": "Whole office network is down",
            "description": "The whole office has no network connectivity, looks like a site outage.",
        },
        "expect_team": "Network",
        "expect_after_create": "Escalated",
        "reply": None,
        "expect_final": "Escalated",
    },
    {
        "name": "finance_stub",
        "ticket": {
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "category": "Finance / Policy",
            "priority": "4 - Low",
            "short_description": "Expense reimbursement missing",
            "description": "My expense report reimbursement hasn't arrived after two weeks.",
        },
        "expect_team": "Finance",
        "expect_after_create": "Escalated",
        "reply": None,
        "expect_final": "Escalated",
    },
    {
        "name": "application_stub",
        "ticket": {
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "category": "Application / NetSuite",
            "priority": "3 - Moderate",
            "short_description": "Outlook keeps crashing",
            "description": "Outlook crashes when I open it after the latest update.",
        },
        "expect_team": "Application",
        "expect_after_create": "Escalated",
        "reply": None,
        "expect_final": "Escalated",
    },
]


def run_case(client: httpx.Client, case: dict) -> None:
    created = client.post("/api/tickets", json=case["ticket"])
    created.raise_for_status()
    body = created.json()
    ticket = body["ticket"]
    tid = ticket["id"]
    assert ticket["assignment_group"] == case["expect_team"], (
        f"{case['name']}: team {ticket['assignment_group']} != {case['expect_team']}"
    )
    assert ticket["state"] == case["expect_after_create"], (
        f"{case['name']}: state after create {ticket['state']} != {case['expect_after_create']}"
    )

    final_state = ticket["state"]
    if case["reply"]:
        reply = client.post(
            f"/api/tickets/{tid}/messages",
            json={"body": case["reply"], "role": "employee", "author": case["ticket"]["caller"]},
        )
        reply.raise_for_status()
        final_state = reply.json()["ticket"]["state"]

    assert final_state == case["expect_final"], (
        f"{case['name']}: final {final_state} != {case['expect_final']}"
    )
    print(f"PASS {case['name']}: {tid} -> {final_state} ({case['expect_team']})")


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=60.0)
    health = client.get("/health")
    health.raise_for_status()
    failed = 0
    for case in CASES:
        try:
            run_case(client, case)
        except Exception as exc:
            failed += 1
            print(f"FAIL {case['name']}: {exc}")
    print(f"Done. {len(CASES) - failed}/{len(CASES)} passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
