"""Orchestrator classification: which fixed specialist owns a ticket."""

from __future__ import annotations

import re
from typing import Any

from .llm import ask_json
from .teams import TEAMS, TEAM_LABEL

DEFAULT_TEAM = "application"

KEYWORDS: dict[str, dict[str, int]] = {
    "network": {
        "vpn": 3, "wifi": 3, "wi-fi": 3, "wireless": 3, "dns": 3, "ethernet": 3, "globalprotect": 3,
        "anyconnect": 3, "packet loss": 3, "internet": 2, "network": 2, "router": 2, "firewall": 2,
        "intranet": 2, "outage": 2, "disconnect": 2, "connection": 2, "offline": 2, "no internet": 3,
        "hotspot": 2, "wfh": 2, "can't connect": 2, "cannot connect": 2,
    },
    "endpoint": {
        "laptop": 3, "desktop": 2, "printer": 3, "keyboard": 2, "mouse": 2, "monitor": 2, "dock": 2,
        "battery": 2, "boot": 3, "won't turn on": 3, "blue screen": 3, "bsod": 3, "hardware": 3,
        "peripheral": 2, "webcam": 2, "slow computer": 2, "disk": 2, "ssd": 1,
    },
    "identity": {
        "password": 3, "mfa": 3, "sso": 3, "locked": 3, "locked out": 3, "login": 2, "log in": 2,
        "access request": 3, "permission": 2, "entitle": 2, "okta": 3, "azure ad": 3, "entra": 3,
        "account locked": 3, "password reset": 3, "authentication": 2,
    },
    "application": {
        "netsuite": 3, "salesforce": 3, "jira": 2, "sap": 3, "workday": 2, "erp": 3, "crm": 2,
        "business app": 2, "application": 2, "software license": 2, "license": 1,
    },
    "collaboration": {
        "outlook": 3, "teams": 3, "sharepoint": 3, "onedrive": 3, "email": 3, "mailbox": 3,
        "calendar": 2, "meeting": 2, "zoom": 2, "skype": 1, "inbox": 2,
    },
    "security": {
        "phishing": 3, "malware": 3, "ransomware": 3, "suspicious": 2, "virus": 3, "breach": 3,
        "security alert": 3, "clicked a link": 3, "scam": 2, "compromised": 3,
    },
    "finance": {
        "invoice": 3, "expense": 3, "expenses": 3, "reimbursement": 3, "payroll": 3,
        "purchase order": 3, "vendor": 2, "payment": 2, "concur": 3, "billing": 2, "receipt": 2,
    },
    "hr": {
        "onboarding": 3, "benefits": 3, "pto": 3, "time off": 3, "hr": 3, "people ops": 2,
        "policy": 1, "new hire": 3, "manager change": 2, "payroll inquiry": 1, "handbook": 2,
    },
}


def keyword_scores(text: str) -> dict[str, int]:
    text = text.lower()
    scores = {}
    for team, words in KEYWORDS.items():
        scores[team] = sum(
            w for kw, w in words.items() if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text)
        )
    return scores


def classify_by_rules(text: str) -> dict[str, Any]:
    scores = keyword_scores(text)
    total = sum(scores.values())
    if total == 0:
        return {
            "team": DEFAULT_TEAM,
            "confidence": 0.3,
            "reason": "No strong team keywords; sent to Application for general intake.",
            "method": "rules",
            "scores": scores,
        }
    team = max(TEAMS, key=lambda t: (scores[t], -TEAMS.index(t)))
    confidence = round(scores[team] / total, 2)
    matched = [
        kw for kw in KEYWORDS[team] if re.search(rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])", text.lower())
    ]
    return {
        "team": team,
        "confidence": confidence,
        "reason": f"Matched {TEAM_LABEL[team]} keywords: {', '.join(matched)}.",
        "method": "rules",
        "scores": scores,
    }


_SYSTEM = (
    "You are an enterprise ITSM triage agent. Route the incident to exactly one team:\n"
    "- network: VPN, Wi-Fi, DNS, connectivity, site outages\n"
    "- endpoint: laptop/desktop hardware, printers, peripherals, boot/performance\n"
    "- identity: passwords, MFA, SSO, account lock, access requests\n"
    "- application: business apps (NetSuite, Salesforce, ERP/CRM), app errors\n"
    "- collaboration: Outlook, Teams, email, SharePoint, OneDrive, meetings\n"
    "- security: phishing, malware, suspicious activity, compromise concerns\n"
    "- finance: expenses, invoices, reimbursements, POs, payroll finance ops\n"
    "- hr: onboarding, benefits, PTO, HR policy, people ops\n"
    "Use the original description AND any caller triage answers. "
    'Return {"team": "...", "confidence": 0.0-1.0, "reason": "one sentence"}.'
)


def classify(ticket: dict[str, Any], llm: Any | None = None, extra_context: str = "") -> dict[str, Any]:
    title = ticket.get("title") or ticket.get("short_description") or ""
    description = ticket.get("description") or ""
    text = f"{title}\n{description}\n{extra_context}".strip()
    prompt = f"Short description: {title}\nDescription: {description}"
    if extra_context.strip():
        prompt += f"\nCaller triage answers:\n{extra_context.strip()}"

    result = ask_json(llm, _SYSTEM, prompt)
    if result and result.get("team") in TEAMS:
        try:
            confidence = max(0.0, min(1.0, float(result.get("confidence", 0.7))))
        except (TypeError, ValueError):
            confidence = 0.7
        return {
            "team": result["team"],
            "confidence": confidence,
            "reason": str(result.get("reason", "")),
            "method": "llm",
        }
    return classify_by_rules(text)
