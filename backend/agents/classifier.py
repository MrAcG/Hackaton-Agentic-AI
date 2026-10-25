"""Orchestrator classification: which fixed specialist owns a ticket."""

from __future__ import annotations

import re
from typing import Any

from .llm import ask_json

TEAMS = ("network", "application", "finance")
DEFAULT_TEAM = "application"  # general IT queue when nothing matches

# keyword -> weight. Strong, unambiguous signals get 3; generic words get 1.
KEYWORDS: dict[str, dict[str, int]] = {
    "network": {
        "vpn": 3, "wifi": 3, "wi-fi": 3, "wireless": 3, "dns": 3, "ethernet": 3, "globalprotect": 3,
        "anyconnect": 3, "packet loss": 3, "latency": 2, "internet": 2, "network": 2, "router": 2,
        "firewall": 2, "proxy": 2, "bandwidth": 2, "ping": 2, "intranet": 1, "outage": 1,
        "disconnect": 1, "disconnects": 1, "connection": 1, "connect": 1, "slow": 1, "site can't be reached": 2,
    },
    "application": {
        "outlook": 3, "teams": 2, "excel": 3, "word": 1, "salesforce": 3, "jira": 3, "sso": 3, "mfa": 2,
        "password": 3, "locked": 2, "login": 2, "log in": 2, "crash": 3, "crashes": 3, "install": 2,
        "license": 2, "software": 2, "application": 2, "app": 1, "error": 1, "update": 1, "account": 1,
    },
    "finance": {
        "invoice": 3, "expense": 3, "expenses": 3, "reimbursement": 3, "reimbursed": 3, "payroll": 3,
        "purchase order": 3, "vendor": 2, "payment": 2, "refund": 2, "billing": 2, "budget": 2,
        "cost center": 3, "concur": 3, "accounts payable": 3, "ledger": 3, "po": 1,
    },
}


def keyword_scores(text: str) -> dict[str, int]:
    text = text.lower()
    scores = {}
    for team, words in KEYWORDS.items():
        scores[team] = sum(w for kw, w in words.items() if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text))
    return scores


def classify_by_rules(text: str) -> dict[str, Any]:
    scores = keyword_scores(text)
    total = sum(scores.values())
    if total == 0:
        return {"team": DEFAULT_TEAM, "confidence": 0.3, "reason": "No team keywords matched; sent to the general application queue.", "method": "rules", "scores": scores}
    team = max(TEAMS, key=lambda t: (scores[t], -TEAMS.index(t)))
    confidence = round(scores[team] / total, 2)
    matched = [kw for kw in KEYWORDS[team] if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text.lower())]
    return {"team": team, "confidence": confidence, "reason": f"Matched {team} keywords: {', '.join(matched)}.", "method": "rules", "scores": scores}


_SYSTEM = (
    "You route internal support tickets to exactly one team: "
    "network (VPN, Wi-Fi, DNS, connectivity, outages), "
    "application (software, accounts, passwords, crashes, licenses), "
    "finance (expenses, invoices, payments, payroll, purchase orders). "
    'Return {"team": "...", "confidence": 0.0-1.0, "reason": "one sentence"}.'
)


def classify(ticket: dict[str, Any], llm: Any | None = None) -> dict[str, Any]:
    text = f"{ticket.get('title', '')}\n{ticket.get('description', '')}"
    result = ask_json(llm, _SYSTEM, text)
    if result and result.get("team") in TEAMS:
        try:
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.7))))
        except (TypeError, ValueError):
            confidence = 0.7
        return {"team": result["team"], "confidence": confidence, "reason": str(result.get("reason", "")), "method": "llm"}
    return classify_by_rules(text)
