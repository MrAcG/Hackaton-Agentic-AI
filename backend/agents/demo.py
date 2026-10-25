"""Chat with the agents in a terminal.

    python -m backend.agents.demo                       # type your own ticket
    python -m backend.agents.demo --scenario vpn_auth_expired
    python -m backend.agents.demo --notes               # also print work notes

Scenarios: vpn_auth_expired, weak_wifi, dns_failure, site_outage, healthy.
"""

from __future__ import annotations

import argparse
import itertools

from .service import AgentService
from .tools.network_tools import SCENARIOS

SAMPLE_TICKETS = {
    "vpn_auth_expired": ("VPN not working", "Working from home and the VPN keeps disconnecting, I can't open the intranet."),
    "weak_wifi": ("Wi-Fi really slow", "My Wi-Fi is really slow on the 3rd floor and Teams calls keep freezing."),
    "dns_failure": ("Intranet site can't be reached", "Chrome says the server can't be reached when I open intranet.corp.local."),
    "site_outage": ("No network", "Nobody can get on the network on our floor, the whole office is down."),
    "healthy": ("Network weird", "Something is off with my connection since this morning."),
}


def show(view: dict, seen: int, notes: bool, seen_notes: int) -> tuple[int, int]:
    for msg in view["chat"][seen:]:
        if msg["role"] == "agent":
            print(f"\n[{msg['author']}]\n{msg['content']}")
    if notes:
        for n in view["work_notes"][seen_notes:]:
            print(f"   ~ work note ({n['author']}): {n['note']}")
    return len(view["chat"]), len(view["work_notes"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=SCENARIOS)
    parser.add_argument("--notes", action="store_true", help="print work notes too")
    args = parser.parse_args()

    if args.scenario:
        title, description = SAMPLE_TICKETS[args.scenario]
        print(f"Ticket: {title}\n{description}")
    else:
        title = input("Ticket title: ").strip()
        description = input("Describe the issue: ").strip()

    ticket = {"id": f"DEMO-{next(itertools.count(1))}", "title": title, "description": description, "requester": "Alex"}
    if args.scenario:
        ticket["mock_scenario"] = args.scenario

    svc = AgentService()
    view = svc.start_ticket(ticket)
    print(f"\n-> routed to {view['team']} ({view['classification']['method']}, confidence {view['classification']['confidence']})")
    seen, seen_notes = show(view, 0, args.notes, 0)
    while view["awaiting_user"]:
        reply = input("\nYou: ").strip()
        view = svc.send_message(ticket["id"], reply)
        seen, seen_notes = show(view, seen, args.notes, seen_notes)
    print(f"\nTicket status: {view['status'].upper()}")
    if view["resolution"]:
        print(f"Resolution: {view['resolution']}")
    if view["escalation"]:
        print(f"Escalated to {view['escalation']['to']}: {view['escalation']['reason']}")


if __name__ == "__main__":
    main()
