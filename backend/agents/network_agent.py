r"""Network specialist agent (demo core).

Flow inside the graph:

    triage -> analyze --(user can fix)--> ask_user -> wait_user -> handle_reply --(worked)--> verify -> resolve
                 |     \--(need info)--/                              |   \--(new info)--> rediagnose -> analyze
                 \--(outage / out of turns)----------------------> escalate <--(still broken / unclear)--/

Diagnosis is made from tool output only (see `analyze_diagnostics`); the mock
scenario is hidden ground truth for the tools, never read by the analysis.
"""

from __future__ import annotations

import re
from typing import Any

from .config import AgentSettings
from .kb import KnowledgeBase
from .llm import ask_json, polish
from .state import TicketState, agent_msg, note, user_msg
from .tools.network_tools import FULL_SWEEP, PLANS, SCENARIOS, detect_symptom, run_tool

AGENT = "Network Agent"

ROOT_CAUSES: dict[str, dict[str, Any]] = {
    "site_outage": {
        "label": "Site network outage",
        "summary": "there is an open network outage at your site",
        "user_fixable": False,
        "user_action": None,
        "verify": [],
    },
    "vpn_auth_expired": {
        "label": "Expired VPN auth token",
        "summary": "your VPN session's sign-in token has expired, so the VPN can't reach internal systems",
        "user_fixable": True,
        "user_action": "1. Open the GlobalProtect VPN client and click Sign Out.\n2. Sign back in and approve the MFA prompt on your phone.\n3. Try opening the site or app again.",
        "verify": [("check_vpn_status", {}), ("dns_lookup", {})],
    },
    "dns_failure": {
        "label": "Stale DNS resolver cache",
        "summary": "your computer can't look up internal site names (DNS) because of a stale cache",
        "user_fixable": True,
        "user_action": "1. Open Command Prompt.\n2. Run `ipconfig /flushdns`.\n3. Disconnect and reconnect to the network, then try the site again.",
        "verify": [("dns_lookup", {})],
    },
    "weak_wifi": {
        "label": "Weak Wi-Fi signal (2.4 GHz) causing packet loss",
        "summary": "your Wi-Fi signal is weak (on the 2.4 GHz network), which causes packet loss and slowness",
        "user_fixable": True,
        "user_action": "1. Switch to the 5 GHz network \"Corp-5G\", or move closer to an access point.\n2. If you have a cable nearby, plug into ethernet.\n3. Check whether things feel normal again.",
        "verify": [("check_wifi_signal", {}), ("ping_host", {"host": "10.10.0.1"})],
    },
}


# --------------------------------------------------------------------------- analysis

def latest_run(diagnostics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Tool name -> output for the most recent diagnostic run."""
    if not diagnostics:
        return {}
    run = max(d.get("run", 0) for d in diagnostics)
    return {d["tool"]: d["output"] for d in diagnostics if d.get("run", 0) == run}


def analyze_diagnostics(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    out = latest_run(diagnostics)
    site, vpn, wifi = out.get("check_site_status"), out.get("check_vpn_status"), out.get("check_wifi_signal")
    ping, dns = out.get("ping_host"), out.get("dns_lookup")

    if site and site.get("status") != "operational":
        return {"root_cause": "site_outage", "evidence": f"Site {site['site']} is {site['status']} ({site.get('open_incident')}: {site.get('detail')})", "incident": site.get("open_incident")}
    if vpn and not vpn.get("connected") and vpn.get("last_error"):
        return {"root_cause": "vpn_auth_expired", "evidence": f"VPN disconnected, last error {vpn['last_error']} (last success {vpn.get('last_success')})"}
    if dns and not dns.get("resolved") and "SERVFAIL" in str(dns.get("error")):
        return {"root_cause": "dns_failure", "evidence": f"{dns['hostname']} failed to resolve via {dns.get('server')}: {dns.get('error')}"}
    weak_signal = wifi and wifi.get("rssi_dbm", 0) < -75
    lossy = ping and ping.get("reachable") and ping.get("packet_loss_pct", 0) >= 10
    if weak_signal or lossy:
        parts = []
        if wifi:
            parts.append(f"Wi-Fi {wifi['rssi_dbm']} dBm on {wifi['band']} ({wifi['ssid']})")
        if ping:
            parts.append(f"{ping.get('packet_loss_pct')}% packet loss, {ping.get('avg_latency_ms')} ms to {ping['host']}")
        return {"root_cause": "weak_wifi", "evidence": "; ".join(parts)}
    checked = ", ".join(sorted(out)) or "none"
    return {"root_cause": "unknown", "evidence": f"All checks healthy ({checked})"}


def fmt_results(results: list[dict[str, Any]]) -> str:
    return "; ".join(f"{r['tool']} -> {r['output']}" for r in results)


def is_healthy(result: dict[str, Any]) -> bool:
    o = result["output"]
    tool = result["tool"]
    if tool == "check_vpn_status":
        return bool(o.get("connected"))
    if tool == "dns_lookup":
        return bool(o.get("resolved"))
    if tool == "check_wifi_signal":
        return o.get("rssi_dbm", -100) >= -75
    if tool == "ping_host":
        return bool(o.get("reachable")) and o.get("packet_loss_pct", 100) < 10
    if tool == "check_site_status":
        return o.get("status") == "operational"
    return False


_NEGATIVE = re.compile(r"\b(no|nope|not|still|doesn'?t|didn'?t|isn'?t|won'?t|can'?t|cannot|same|broken|fails?|failed|failing|worse|error)\b")
_POSITIVE = re.compile(r"\b(yes|yep|yeah|yup|works?|working|worked|fixed|resolved|done|ok|okay|great|perfect|thanks|thank|connected|better|good|fine|solved)\b")


def interpret_reply(text: str, llm: Any | None = None) -> str:
    """'positive' (fix worked), 'negative' (still broken) or 'unclear'."""
    result = ask_json(
        llm,
        "An employee was asked to try an IT fix and report back. Classify their reply as "
        '"positive" (it works now), "negative" (still broken) or "unclear". Return {"intent": "..."}.',
        text,
    )
    if result and result.get("intent") in ("positive", "negative", "unclear"):
        return result["intent"]
    lowered = text.lower()
    if _NEGATIVE.search(lowered):
        return "negative"
    if _POSITIVE.search(lowered):
        return "positive"
    return "unclear"


# --------------------------------------------------------------------------- nodes

class NetworkAgent:
    def __init__(self, settings: AgentSettings, kb: KnowledgeBase, llm: Any | None = None):
        self.settings = settings
        self.kb = kb
        self.llm = llm

    def _say(self, text: str) -> dict[str, Any]:
        return agent_msg(AGENT, polish(self.llm, text))

    def _run(self, plan, scenario: str, remediated: bool, run: int) -> list[dict[str, Any]]:
        return [{**run_tool(name, scenario, remediated, **args), "run": run} for name, args in plan]

    @staticmethod
    def _scenario(state: TicketState, extra_text: str = "") -> str:
        ticket = state["ticket"]
        forced = ticket.get("mock_scenario")
        if forced in SCENARIOS:
            return forced
        return detect_symptom(f"{ticket.get('title', '')} {ticket.get('description', '')} {extra_text}")

    def triage(self, state: TicketState) -> dict[str, Any]:
        ticket = state["ticket"]
        text = f"{ticket.get('title', '')}\n{ticket.get('description', '')}"
        hits = self.kb.search(text, team="network", k=3)
        symptom = detect_symptom(text)
        plan = PLANS.get(symptom, FULL_SWEEP)
        scenario = self._scenario(state)
        results = self._run(plan, scenario, remediated=False, run=1)
        kb_line = ", ".join(f"{h['title']} ({h['doc_id']})" for h in hits) or "no matching runbooks"
        notes = [
            note(AGENT, f"Picked up ticket. Suspected symptom: {symptom}. KB consulted: {kb_line}."),
            note(AGENT, f"Diagnostics run 1 (targeted): {fmt_results(results)}"),
        ]
        # Targeted checks found nothing: broaden before asking the employee.
        if plan is not FULL_SWEEP and analyze_diagnostics(results)["root_cause"] == "unknown":
            sweep = self._run(FULL_SWEEP, scenario, remediated=False, run=2)
            results += sweep
            notes.append(note(AGENT, f"Targeted checks inconclusive. Diagnostics run 2 (full sweep): {fmt_results(sweep)}"))
        return {
            "status": "in_progress",
            "symptom": symptom,
            "kb_hits": hits,
            "diagnostics": results,
            "remediated": False,
            "user_turns": state.get("user_turns", 0),
            "work_notes": notes,
        }

    def analyze(self, state: TicketState) -> dict[str, Any]:
        findings = analyze_diagnostics(state.get("diagnostics", []))
        cause = findings["root_cause"]
        info = ROOT_CAUSES.get(cause)
        if info and not info["user_fixable"]:
            step = "escalate"
        elif info:
            step = "ask_fix"
        elif state.get("user_turns", 0) < self.settings.max_user_turns:
            step = "ask_clarify"
        else:
            step = "escalate"
        return {
            "findings": findings,
            "next_step": step,
            "work_notes": [note(AGENT, f"Analysis: root cause = {cause}. Evidence: {findings['evidence']}. Next: {step}.")],
        }

    def ask_user(self, state: TicketState) -> dict[str, Any]:
        name = state["ticket"].get("requester") or "there"
        cause = state["findings"]["root_cause"]
        pending = state.get("pending")
        if pending and state.get("next_step") == "ask_again":
            question = "Sorry, I couldn't tell whether that fixed it. Is it working now? (yes / no)"
            kind = pending["kind"]
        elif cause in ROOT_CAUSES:
            info = ROOT_CAUSES[cause]
            question = (
                f"Hi {name}, I ran network diagnostics and found the likely cause: {info['summary']}.\n\n"
                f"Please try this:\n{info['user_action']}\n\nReply here to let me know if it worked."
            )
            kind = "fix"
        else:
            question = (
                f"Hi {name}, I ran a full set of network checks (VPN, Wi-Fi signal, DNS, gateway) and everything "
                "looks healthy from my side. Can you tell me more: what exactly fails (a specific site or app), "
                "any error message you see, and whether you're in the office or working remotely?"
            )
            kind = "clarify"
        message = self._say(question)
        return {
            "status": "awaiting_user",
            "pending": {"kind": kind, "question": message["content"], "root_cause": cause},
            "chat": [message],
        }

    def wait_user(self, state: TicketState) -> dict[str, Any]:
        # Pauses the graph. The service resumes it with Command(resume=<user text>).
        from langgraph.types import interrupt  # imported here so the pure logic is testable without LangGraph

        reply = interrupt({"ticket_id": state["ticket"].get("id"), "question": state["pending"]["question"]})
        reply = str(reply).strip()
        return {
            "status": "in_progress",
            "last_user_reply": reply,
            "user_turns": state.get("user_turns", 0) + 1,
            "chat": [user_msg(state["ticket"].get("requester") or "Employee", reply)],
        }

    def handle_reply(self, state: TicketState) -> dict[str, Any]:
        pending = state.get("pending") or {}
        reply = state.get("last_user_reply", "")
        turns_left = state.get("user_turns", 0) < self.settings.max_user_turns
        if pending.get("kind") == "clarify":
            step, intent = "rediagnose", "info"
        else:
            intent = interpret_reply(reply, self.llm)
            if intent == "positive":
                step = "verify"
            elif intent == "negative":
                step = "escalate"
            else:
                step = "ask_again" if turns_left else "escalate"
        return {
            "next_step": step,
            "pending": pending if step == "ask_again" else None,
            "work_notes": [note(AGENT, f"User replied ({intent}): \"{reply}\". Next: {step}.")],
        }

    def verify(self, state: TicketState) -> dict[str, Any]:
        cause = state["findings"]["root_cause"]
        run = max((d.get("run", 0) for d in state.get("diagnostics", [])), default=0) + 1
        results = self._run(ROOT_CAUSES[cause]["verify"], self._scenario(state), remediated=True, run=run)
        healthy = all(is_healthy(r) for r in results)
        return {
            "remediated": True,
            "diagnostics": results,
            "next_step": "resolve" if healthy else "escalate",
            "work_notes": [note(AGENT, f"Verification run {run}: {fmt_results(results)}. Healthy: {healthy}.")],
        }

    def rediagnose(self, state: TicketState) -> dict[str, Any]:
        run = max((d.get("run", 0) for d in state.get("diagnostics", [])), default=0) + 1
        scenario = self._scenario(state, extra_text=state.get("last_user_reply", ""))
        results = self._run(FULL_SWEEP, scenario, remediated=False, run=run)
        return {
            "symptom": detect_symptom(state.get("last_user_reply", "")),
            "diagnostics": results,
            "work_notes": [note(AGENT, f"Diagnostics run {run} (full sweep after new info): {fmt_results(results)}")],
        }

    def resolve(self, state: TicketState) -> dict[str, Any]:
        cause = state["findings"]["root_cause"]
        resolution = f"Root cause: {ROOT_CAUSES[cause]['label']}. User applied the documented fix; verification checks passed."
        return {
            "status": "resolved",
            "resolution": resolution,
            "pending": None,
            "chat": [self._say("Thanks! I re-ran the checks and everything looks healthy now, so I'm marking this ticket resolved. If the problem comes back, just open a new ticket.")],
            "work_notes": [note(AGENT, f"RESOLVED. {resolution}")],
        }

    def escalate(self, state: TicketState) -> dict[str, Any]:
        findings = state.get("findings") or {}
        cause = findings.get("root_cause", "unknown")
        if cause == "site_outage":
            reason = f"Known site outage ({findings.get('incident')}); not fixable on the user's device."
            user_text = f"This is part of a known network outage at your site ({findings.get('incident')}). I've linked your ticket to it and escalated to the Network L2 team, who are already working on it. You'll get an update here."
        elif cause in ROOT_CAUSES and state.get("last_user_reply"):
            reason = f"Suspected {cause}; documented fix did not resolve it per user."
            user_text = "Sorry that didn't fix it. I've escalated this to the Network L2 team and attached all my diagnostics, so you won't need to repeat anything. They'll follow up on this ticket."
        else:
            reason = f"No root cause found after {state.get('user_turns', 0)} follow-up(s)."
            user_text = "I couldn't pin this down automatically, so I've escalated it to the Network L2 team with everything I checked. They'll follow up on this ticket."
        escalation = {
            "to": "Network L2",
            "reason": reason,
            "suspected_cause": cause,
            "evidence": findings.get("evidence"),
            "diagnostic_runs": max((d.get("run", 0) for d in state.get("diagnostics", [])), default=0),
        }
        return {
            "status": "escalated",
            "escalation": escalation,
            "pending": None,
            "chat": [self._say(user_text)],
            "work_notes": [note(AGENT, f"ESCALATED to Network L2. {reason} Evidence: {findings.get('evidence')}")],
        }


def route_after_analyze(state: TicketState) -> str:
    return "escalate" if state["next_step"] == "escalate" else "ask_user"


def route_after_reply(state: TicketState) -> str:
    return {"verify": "verify", "rediagnose": "rediagnose", "ask_again": "ask_user"}.get(state["next_step"], "escalate")


def route_after_verify(state: TicketState) -> str:
    return "resolve" if state["next_step"] == "resolve" else "escalate"
