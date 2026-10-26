"""HTTP end-to-end scenarios: triage -> specialist -> resolve/escalate."""

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
            "priority": "2 - High",
            "short_description": "VPN authentication failed",
            "description": "My VPN says authentication expired and I cannot get on the corporate network.",
        },
        "triage": "Network / VPN from home — GlobalProtect auth expired",
        "expect_team": "Network",
        "replies_after_route": ["I re-authenticated with MFA and it works now"],
        "expect_final": "Resolved",
    },
    {
        "name": "finance_stub",
        "ticket": {
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "priority": "4 - Low",
            "short_description": "Expense reimbursement missing",
            "description": "My expense report reimbursement hasn't arrived after two weeks.",
        },
        "triage": "Finance / expense reimbursement in Concur",
        "expect_team": "Finance",
        "replies_after_route": ["Submitted in Concur two weeks ago for about $240"],
        "expect_final": "Escalated",
    },
    {
        "name": "identity_stub",
        "ticket": {
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "priority": "2 - High",
            "short_description": "Can't get past MFA",
            "description": "Password works but MFA loops and I think I'm locked out.",
        },
        "triage": "Login / MFA / password — account locked feeling",
        "expect_team": "Identity",
        "replies_after_route": ["SSO to Outlook, MFA never finishes"],
        "expect_final": "Escalated",
    },
    {
        "name": "collaboration_stub",
        "ticket": {
            "caller": "Alex Rivera",
            "caller_email": "alex.rivera@company.example",
            "priority": "3 - Moderate",
            "short_description": "Outlook keeps crashing",
            "description": "Outlook crashes when I open it after the latest update.",
        },
        "triage": "Email / Outlook / Teams collaboration issue",
        "expect_team": "Collaboration",
        "replies_after_route": ["Desktop Outlook, crashes on launch"],
        "expect_final": "Escalated",
    },
]


def run_case(client: httpx.Client, case: dict) -> None:
    created = client.post("/api/tickets", json=case["ticket"])
    created.raise_for_status()
    body = created.json()
    ticket = body["ticket"]
    tid = ticket["id"]
    assert ticket["state"] == "Pending", f"{case['name']}: expected triage Pending, got {ticket['state']}"

    triage = client.post(
        f"/api/tickets/{tid}/messages",
        json={"body": case["triage"], "role": "employee", "author": case["ticket"]["caller"]},
    )
    triage.raise_for_status()
    after = triage.json()["ticket"]
    assert after["assignment_group"] == case["expect_team"], (
        f"{case['name']}: team {after['assignment_group']} != {case['expect_team']}"
    )

    final_state = after["state"]
    for text in case.get("replies_after_route") or []:
        reply = client.post(
            f"/api/tickets/{tid}/messages",
            json={"body": text, "role": "employee", "author": case["ticket"]["caller"]},
        )
        reply.raise_for_status()
        final_state = reply.json()["ticket"]["state"]

    assert final_state == case["expect_final"], f"{case['name']}: final {final_state} != {case['expect_final']}"
    print(f"PASS {case['name']}: {tid} -> {final_state} ({case['expect_team']})")


def main() -> int:
    client = httpx.Client(base_url=BASE, timeout=90.0)
    client.get("/health").raise_for_status()
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
