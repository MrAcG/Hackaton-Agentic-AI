"""Builds the LangGraph: triage intake -> classify -> fixed specialist."""

from __future__ import annotations

from typing import Any

from .classifier import classify
from .config import AgentSettings
from .kb import KnowledgeBase
from .llm import polish
from .network_agent import NetworkAgent, route_after_analyze, route_after_reply, route_after_verify
from .state import TicketState, agent_msg, note, user_msg
from .stub_agents import StubAgent
from .teams import ORCHESTRATOR_INTAKE, TEAM_LABEL, TEAMS

ORCHESTRATOR = "Orchestrator"

STUB_TEAMS = ("endpoint", "identity", "application", "collaboration", "security", "finance", "hr")

ENTRY_NODES = {
    "network": "network_triage",
    **{t: f"{t}_intake" for t in STUB_TEAMS},
}


def make_orchestrator_intake(llm: Any | None):
    def intake(state: TicketState) -> dict[str, Any]:
        name = state["ticket"].get("requester") or "there"
        text = f"Hi {name}, {ORCHESTRATOR_INTAKE}"
        message = agent_msg(ORCHESTRATOR, polish(llm, text))
        return {
            "status": "awaiting_user",
            "pending": {"kind": "triage", "question": message["content"]},
            "chat": [message],
            "work_notes": [note(ORCHESTRATOR, "Triage intake: collecting context before assigning a specialist team.")],
        }

    return intake


def orchestrator_wait(state: TicketState) -> dict[str, Any]:
    from langgraph.types import interrupt

    reply = interrupt({"ticket_id": state["ticket"].get("id"), "question": (state.get("pending") or {}).get("question")})
    reply = str(reply).strip()
    return {
        "status": "in_progress",
        "last_user_reply": reply,
        "user_turns": 0,  # specialist phase counts its own turns
        "chat": [user_msg(state["ticket"].get("requester") or "Employee", reply)],
        "work_notes": [note(ORCHESTRATOR, f"Triage reply captured: {reply[:240]}")],
    }


def make_classify_node(settings: AgentSettings, llm: Any | None):
    def classify_node(state: TicketState) -> dict[str, Any]:
        ticket = dict(state.get("ticket") or {})
        reply = (state.get("last_user_reply") or "").strip()
        if reply:
            base = (ticket.get("description") or "").rstrip()
            ticket["description"] = f"{base}\n\nCaller triage answers:\n{reply}".strip()
        result = classify(ticket, llm, extra_context=reply)
        if result["team"] not in TEAMS:
            result = {**result, "team": "application"}
        flag = "" if result["confidence"] >= settings.min_route_confidence else " LOW CONFIDENCE: please review routing."
        label = TEAM_LABEL.get(result["team"], result["team"])
        return {
            "ticket": ticket,
            "status": "in_progress",
            "classification": result,
            "team": result["team"],
            "last_user_reply": "",
            "pending": None,
            "work_notes": [
                note(
                    ORCHESTRATOR,
                    f"Assigned to {label} agent ({result['method']}, confidence {result['confidence']:.2f}). "
                    f"{result['reason']}{flag}",
                )
            ],
        }

    return classify_node


def route_to_team(state: TicketState) -> str:
    return ENTRY_NODES[state["team"]]


def build_graph(settings: AgentSettings, kb: KnowledgeBase, llm: Any | None = None, checkpointer: Any | None = None):
    from langgraph.graph import END, START, StateGraph

    net = NetworkAgent(settings, kb, llm)
    g = StateGraph(TicketState)

    g.add_node("orchestrator_intake", make_orchestrator_intake(llm))
    g.add_node("orchestrator_wait", orchestrator_wait)
    g.add_node("classify", make_classify_node(settings, llm))

    g.add_node("network_triage", net.triage)
    g.add_node("network_analyze", net.analyze)
    g.add_node("network_ask_user", net.ask_user)
    g.add_node("network_wait_user", net.wait_user)
    g.add_node("network_handle_reply", net.handle_reply)
    g.add_node("network_verify", net.verify)
    g.add_node("network_rediagnose", net.rediagnose)
    g.add_node("network_resolve", net.resolve)
    g.add_node("network_escalate", net.escalate)

    stub_agents = {t: StubAgent(t, kb, llm) for t in STUB_TEAMS}
    for team, agent in stub_agents.items():
        g.add_node(f"{team}_intake", agent.intake)
        g.add_node(f"{team}_wait", agent.wait)
        g.add_node(f"{team}_finish", agent.finish)

    g.add_edge(START, "orchestrator_intake")
    g.add_edge("orchestrator_intake", "orchestrator_wait")
    g.add_edge("orchestrator_wait", "classify")
    g.add_conditional_edges("classify", route_to_team, list(ENTRY_NODES.values()))

    g.add_edge("network_triage", "network_analyze")
    g.add_conditional_edges("network_analyze", route_after_analyze, {"ask_user": "network_ask_user", "escalate": "network_escalate"})
    g.add_edge("network_ask_user", "network_wait_user")
    g.add_edge("network_wait_user", "network_handle_reply")
    g.add_conditional_edges(
        "network_handle_reply",
        route_after_reply,
        {"verify": "network_verify", "rediagnose": "network_rediagnose", "ask_user": "network_ask_user", "escalate": "network_escalate"},
    )
    g.add_conditional_edges("network_verify", route_after_verify, {"resolve": "network_resolve", "escalate": "network_escalate"})
    g.add_edge("network_rediagnose", "network_analyze")

    for team in STUB_TEAMS:
        g.add_edge(f"{team}_intake", f"{team}_wait")
        g.add_edge(f"{team}_wait", f"{team}_finish")
        g.add_edge(f"{team}_finish", END)

    for terminal in ("network_resolve", "network_escalate"):
        g.add_edge(terminal, END)

    if checkpointer is None:
        try:
            from langgraph.checkpoint.memory import InMemorySaver as checkpointer_cls
        except ImportError:
            from langgraph.checkpoint.memory import MemorySaver as checkpointer_cls
        checkpointer = checkpointer_cls()
    return g.compile(checkpointer=checkpointer)
