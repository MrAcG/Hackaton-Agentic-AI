"""Mock network diagnostics.

Each tool returns what a real probe would report, driven by a hidden
"scenario" (the ground truth for the demo) and whether the user has already
applied a fix. The tools are pure functions of (scenario, remediated, args), so
results are reproducible and survive a pause/resume of the ticket.

The Network agent never reads the scenario directly: it only sees tool output
and has to diagnose from that evidence.
"""

from __future__ import annotations

import re
from typing import Any, Callable

SCENARIOS = ("vpn_auth_expired", "weak_wifi", "dns_failure", "site_outage", "healthy")

INTERNAL_HOST = "intranet.corp.local"
GATEWAY = "10.10.0.1"
CORE_SWITCH = "core-sw-01.bos.corp.local"

# Symptom keywords -> the scenario a ticket most likely describes.
# Order matters: earlier entries win when several match.
_SYMPTOM_PATTERNS: list[tuple[str, tuple[str, ...]]] = [
    ("site_outage", (
        "outage", "everyone", "whole office", "entire floor", "nobody can", "all users", "whole team",
        "building is down", "site is down", "entire site",
    )),
    ("vpn_auth_expired", (
        "vpn", "globalprotect", "anyconnect", "remote access", "working from home", "wfh",
        "auth token", "authentication expired", "mfa loop", "can't sign in to vpn", "cannot sign in to vpn",
        "vpn won't connect", "vpn will not connect", "corporate network from home",
    )),
    ("dns_failure", (
        "dns", "server not found", "can't be reached", "cannot be reached", "can't resolve", "not resolving",
        "hostname", "intranet", "site can't be reached", "dns_probe_finished", "name resolution",
    )),
    ("weak_wifi", (
        "wifi", "wi-fi", "wireless", "signal", "slow", "lag", "laggy", "drops", "freez", "buffer",
        "packet loss", "keeps disconnecting", "spotty", "bars", "access point", "ethernet",
    )),
]


def detect_symptom(text: str) -> str:
    text = text.lower()
    for scenario, words in _SYMPTOM_PATTERNS:
        if any(w in text for w in words):
            return scenario
    return "healthy"  # nothing recognisable: needs a broad sweep


def _internal(host: str) -> bool:
    return host.endswith(".corp.local") or bool(re.match(r"^10\.", host))


def check_vpn_status(scenario: str, remediated: bool, user: str = "employee") -> dict[str, Any]:
    if scenario == "vpn_auth_expired" and not remediated:
        return {"user": user, "connected": False, "client": "GlobalProtect 6.2", "last_error": "AUTH_TOKEN_EXPIRED", "last_success": "3 days ago"}
    return {"user": user, "connected": True, "client": "GlobalProtect 6.2", "last_error": None, "last_success": "just now"}


def check_wifi_signal(scenario: str, remediated: bool, device: str = "laptop") -> dict[str, Any]:
    if scenario == "weak_wifi" and not remediated:
        return {"device": device, "ssid": "Corp-2G", "band": "2.4GHz", "rssi_dbm": -82, "access_point": "ap-bos-3f-07"}
    return {"device": device, "ssid": "Corp-5G", "band": "5GHz", "rssi_dbm": -51, "access_point": "ap-bos-3f-02"}


def ping_host(scenario: str, remediated: bool, host: str = GATEWAY) -> dict[str, Any]:
    if scenario == "site_outage" and _internal(host):
        return {"host": host, "reachable": False, "packet_loss_pct": 100, "avg_latency_ms": None}
    if scenario == "vpn_auth_expired" and not remediated and _internal(host):
        return {"host": host, "reachable": False, "packet_loss_pct": 100, "avg_latency_ms": None}
    if scenario == "weak_wifi" and not remediated:
        return {"host": host, "reachable": True, "packet_loss_pct": 18, "avg_latency_ms": 240}
    return {"host": host, "reachable": True, "packet_loss_pct": 0, "avg_latency_ms": 12}


def dns_lookup(scenario: str, remediated: bool, hostname: str = INTERNAL_HOST) -> dict[str, Any]:
    if scenario == "dns_failure" and not remediated:
        return {"hostname": hostname, "resolved": False, "server": "10.10.0.2", "error": "SERVFAIL (stale resolver cache)"}
    if scenario in ("vpn_auth_expired", "site_outage") and not remediated and _internal(hostname):
        return {"hostname": hostname, "resolved": False, "server": None, "error": "timeout: no DNS server reachable"}
    return {"hostname": hostname, "resolved": True, "server": "10.10.0.3", "address": "10.20.4.15"}


def check_site_status(scenario: str, remediated: bool, site: str = "BOS-HQ") -> dict[str, Any]:
    if scenario == "site_outage":  # a user cannot fix an outage
        return {"site": site, "status": "degraded", "open_incident": "INC-NET-0042", "detail": f"Core switch {CORE_SWITCH} down"}
    return {"site": site, "status": "operational", "open_incident": None}


TOOLS: dict[str, Callable[..., dict[str, Any]]] = {
    "check_site_status": check_site_status,
    "check_vpn_status": check_vpn_status,
    "check_wifi_signal": check_wifi_signal,
    "ping_host": ping_host,
    "dns_lookup": dns_lookup,
}

# Which probes to run for a suspected symptom. Site status always runs first,
# because an outage makes every other check misleading.
PLANS: dict[str, list[tuple[str, dict[str, Any]]]] = {
    "vpn_auth_expired": [("check_site_status", {}), ("check_vpn_status", {}), ("ping_host", {"host": GATEWAY}), ("dns_lookup", {})],
    "weak_wifi": [("check_site_status", {}), ("check_wifi_signal", {}), ("ping_host", {"host": GATEWAY})],
    "dns_failure": [("check_site_status", {}), ("dns_lookup", {}), ("ping_host", {"host": GATEWAY})],
    "site_outage": [("check_site_status", {}), ("ping_host", {"host": CORE_SWITCH})],
}
FULL_SWEEP: list[tuple[str, dict[str, Any]]] = [
    ("check_site_status", {}), ("check_vpn_status", {}), ("check_wifi_signal", {}),
    ("ping_host", {"host": GATEWAY}), ("dns_lookup", {}),
]


def run_tool(name: str, scenario: str, remediated: bool, **args: Any) -> dict[str, Any]:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario {scenario!r}; expected one of {SCENARIOS}")
    output = TOOLS[name](scenario, remediated, **args)
    return {"tool": name, "args": args, "output": output}
