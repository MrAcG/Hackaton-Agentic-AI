"""Builds the LangGraph for one ticket: orchestrator -> fixed specialist."""

from __future__ import annotations

from typing import Any

from .classifier import classify
from .config import AgentSettings
from .kb import KnowledgeBase
from .network_agent import NetworkAgent, route_after_analyze, route_after_reply, route_after_verify
from .state import TicketState, note
from .stub_agents import StubAgent

ORCHESTRATOR = "Orchestrator"
ENTRY_NODES = {"network": "network_triage", "application": "application_agent", "finance": "finance_agent"}


def make_classify_node(settings: AgentSettings, llm: Any | None):
    def classify_node(state: TicketState) -> dict[str, Any]:
        result = classify(state["ticket"], llm)
        flag = "" if result["confidence"] >= settings.min_route_confidence else " LOW CONFIDENCE: please review routing."
        return {
            "status": "in_progress",
            "classification": result,
            "team": result["team"],
            "work_notes": [note(ORCHESTRATOR, f"Routed to {result['team']} agent ({result['method']}, confidence {result['confidence']:.2f}). {result['reason']}{flag}")],
        }

    return classify_node


def route_to_team(state: TicketState) -> str:
    return ENTRY_NODES[state["team"]]


def build_graph(settings: AgentSettings, kb: KnowledgeBase, llm: Any | None = None, checkpointer: Any | None = None):
    from langgraph.graph import END, START, StateGraph

    net = NetworkAgent(settings, kb, llm)
    g = StateGraph(TicketState)

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
    g.add_node("application_agent", StubAgent("application", kb, llm))
    g.add_node("finance_agent", StubAgent("finance", kb, llm))

    g.add_edge(START, "classify")
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
    for terminal in ("network_resolve", "network_escalate", "application_agent", "finance_agent"):
        g.add_edge(terminal, END)

    if checkpointer is None:
        try:
            from langgraph.checkpoint.memory import InMemorySaver as checkpointer_cls
        except ImportError:  # older langgraph
            from langgraph.checkpoint.memory import MemorySaver as checkpointer_cls
        checkpointer = checkpointer_cls()
    return g.compile(checkpointer=checkpointer)
