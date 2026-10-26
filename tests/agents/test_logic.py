"""Agent logic tests that need no LangGraph and no LLM."""

import unittest

from backend.agents.classifier import classify
from backend.agents.config import AgentSettings
from backend.agents.kb import KeywordKnowledgeBase, section
from backend.agents.network_agent import NetworkAgent, analyze_diagnostics, interpret_reply
from backend.agents.stub_agents import StubAgent
from backend.agents.tools.network_tools import FULL_SWEEP, PLANS, detect_symptom, run_tool

SETTINGS = AgentSettings()
KB = KeywordKnowledgeBase(SETTINGS.kb_dir)


def sweep(scenario, remediated=False, plan=FULL_SWEEP, run=1):
    return [{**run_tool(name, scenario, remediated, **args), "run": run} for name, args in plan]


class ClassifierTests(unittest.TestCase):
    def check(self, title, description, team):
        self.assertEqual(classify({"title": title, "description": description})["team"], team)

    def test_routes_network(self):
        self.check("VPN down", "GlobalProtect keeps disconnecting", "network")
        self.check("Slow wifi", "packet loss on wi-fi in the office", "network")

    def test_routes_application(self):
        self.check("NetSuite error", "NetSuite will not save the journal entry", "application")

    def test_routes_collaboration(self):
        self.check("Outlook crash", "Outlook crashes when I open it", "collaboration")

    def test_routes_identity(self):
        self.check("Locked out", "my password expired and my account is locked", "identity")

    def test_routes_finance(self):
        self.check("Reimbursement", "my expense report reimbursement hasn't arrived", "finance")
        self.check("Vendor invoice", "vendor says invoice for purchase order 4411 is unpaid", "finance")

    def test_unknown_goes_to_default_with_low_confidence(self):
        result = classify({"title": "Help", "description": "something weird"})
        self.assertEqual(result["team"], "application")
        self.assertLess(result["confidence"], 0.5)

    def test_falls_back_to_rules_when_llm_returns_garbage(self):
        class BadLLM:
            def invoke(self, _):
                return type("R", (), {"content": "not json"})()

        result = classify({"title": "VPN", "description": "vpn down"}, BadLLM())
        self.assertEqual((result["team"], result["method"]), ("network", "rules"))

    def test_uses_llm_when_valid(self):
        class GoodLLM:
            def invoke(self, _):
                return type("R", (), {"content": '{"team": "finance", "confidence": 0.9, "reason": "payroll"}'})()

        result = classify({"title": "x", "description": "y"}, GoodLLM())
        self.assertEqual((result["team"], result["method"]), ("finance", "llm"))


class KnowledgeBaseTests(unittest.TestCase):
    def test_finds_vpn_runbook(self):
        hits = KB.search("VPN disconnecting token expired", team="network")
        self.assertEqual(hits[0]["doc_id"], "network/vpn-auth")

    def test_team_filter(self):
        self.assertTrue(all(h["team"] == "finance" for h in KB.search("invoice payment vendor", team="finance")))

    def test_section(self):
        self.assertIn("ipconfig /flushdns", section(KB.search("dns", team="network")[0]["content"], "Resolution"))


class DiagnosisTests(unittest.TestCase):
    def test_symptom_detection(self):
        self.assertEqual(detect_symptom("the VPN is broken"), "vpn_auth_expired")
        self.assertEqual(detect_symptom("whole office has no network, outage"), "site_outage")
        self.assertEqual(detect_symptom("wifi is slow"), "weak_wifi")
        self.assertEqual(detect_symptom("server not found for intranet"), "dns_failure")
        self.assertEqual(detect_symptom("weird"), "healthy")

    def test_each_scenario_is_diagnosed_from_full_sweep(self):
        for scenario in ("vpn_auth_expired", "weak_wifi", "dns_failure", "site_outage"):
            with self.subTest(scenario=scenario):
                self.assertEqual(analyze_diagnostics(sweep(scenario))["root_cause"], scenario)

    def test_each_scenario_is_diagnosed_from_its_own_plan(self):
        for scenario, plan in PLANS.items():
            with self.subTest(scenario=scenario):
                self.assertEqual(analyze_diagnostics(sweep(scenario, plan=plan))["root_cause"], scenario)

    def test_healthy_and_remediated_are_unknown(self):
        self.assertEqual(analyze_diagnostics(sweep("healthy"))["root_cause"], "unknown")
        self.assertEqual(analyze_diagnostics(sweep("weak_wifi", remediated=True))["root_cause"], "unknown")

    def test_only_latest_run_counts(self):
        diags = sweep("weak_wifi", run=1) + sweep("weak_wifi", remediated=True, run=2)
        self.assertEqual(analyze_diagnostics(diags)["root_cause"], "unknown")

    def test_outage_cannot_be_remediated_by_user(self):
        self.assertEqual(analyze_diagnostics(sweep("site_outage", remediated=True))["root_cause"], "site_outage")

    def test_interpret_reply(self):
        for text, intent in [
            ("yes it works now, thanks!", "positive"),
            ("done", "positive"),
            ("still doesn't work", "negative"),
            ("no", "negative"),
            ("hmm let me check", "unclear"),
        ]:
            with self.subTest(text=text):
                self.assertEqual(interpret_reply(text), intent)


def merge(state, update):
    """Apply a node update the way LangGraph does (append for the log fields)."""
    for key, value in update.items():
        if key in ("chat", "work_notes", "diagnostics"):
            state[key] = state.get(key, []) + value
        else:
            state[key] = value
    return state


class NetworkNodeFlowTests(unittest.TestCase):
    """Drives the node functions in graph order, without LangGraph."""

    def setUp(self):
        self.agent = NetworkAgent(SETTINGS, KB)

    def start(self, title, description, scenario=None):
        ticket = {"id": "T1", "title": title, "description": description, "requester": "Sam"}
        if scenario:
            ticket["mock_scenario"] = scenario
        state = {"ticket": ticket, "chat": [], "work_notes": [], "diagnostics": [], "user_turns": 0}
        merge(state, self.agent.triage(state))
        merge(state, self.agent.analyze(state))
        return state

    def reply(self, state, text):
        merge(state, {"last_user_reply": text, "user_turns": state["user_turns"] + 1})
        merge(state, self.agent.handle_reply(state))
        return state

    def test_vpn_fix_then_verify_resolves(self):
        s = self.start("VPN broken", "vpn keeps disconnecting")
        self.assertEqual(s["next_step"], "ask_fix")
        merge(s, self.agent.ask_user(s))
        self.assertEqual(s["status"], "awaiting_user")
        self.assertIn("MFA", s["chat"][-1]["content"])
        self.reply(s, "done, it works")
        self.assertEqual(s["next_step"], "verify")
        merge(s, self.agent.verify(s))
        self.assertEqual(s["next_step"], "resolve")
        merge(s, self.agent.resolve(s))
        self.assertEqual(s["status"], "resolved")

    def test_fix_not_working_escalates(self):
        s = self.start("Wifi slow", "wifi slow and freezing")
        merge(s, self.agent.ask_user(s))
        self.reply(s, "still slow, didn't help")
        self.assertEqual(s["next_step"], "escalate")
        merge(s, self.agent.escalate(s))
        self.assertEqual((s["status"], s["escalation"]["to"]), ("escalated", "Network L2"))

    def test_outage_escalates_without_asking(self):
        s = self.start("No network", "whole office is down")
        self.assertEqual(s["next_step"], "escalate")
        merge(s, self.agent.escalate(s))
        self.assertIn("INC-NET-0042", s["escalation"]["reason"])

    def test_mock_scenario_overrides_text(self):
        s = self.start("Intranet slow", "the intranet is slow", scenario="dns_failure")
        self.assertEqual(s["findings"]["root_cause"], "dns_failure")

    def test_clarify_then_rediagnose_finds_cause(self):
        s = self.start("Network weird", "something is off with my connection")
        self.assertEqual(s["next_step"], "ask_clarify")
        merge(s, self.agent.ask_user(s))
        self.assertEqual(s["pending"]["kind"], "clarify")
        self.reply(s, "I'm working from home on the VPN")
        self.assertEqual(s["next_step"], "rediagnose")
        merge(s, self.agent.rediagnose(s))
        merge(s, self.agent.analyze(s))
        self.assertEqual((s["findings"]["root_cause"], s["next_step"]), ("vpn_auth_expired", "ask_fix"))

    def test_unclear_reply_asks_again_then_escalates(self):
        s = self.start("VPN broken", "vpn down")
        merge(s, self.agent.ask_user(s))
        for _ in range(SETTINGS.max_user_turns - 1):
            self.reply(s, "hmm")
            self.assertEqual(s["next_step"], "ask_again")
            merge(s, self.agent.ask_user(s))
            self.assertIn("yes/no", s["chat"][-1]["content"].replace(" ", ""))
        self.reply(s, "hmm")
        self.assertEqual(s["next_step"], "escalate")

    def test_clarify_loop_is_bounded(self):
        s = self.start("Network weird", "something is off")
        for _ in range(SETTINGS.max_user_turns):
            self.assertEqual(s["next_step"], "ask_clarify")
            merge(s, self.agent.ask_user(s))
            self.reply(s, "it's just weird")
            merge(s, self.agent.rediagnose(s))
            merge(s, self.agent.analyze(s))
        self.assertEqual(s["next_step"], "escalate")


class StubAgentTests(unittest.TestCase):
    def test_finance_intake_then_finish_escalates(self):
        agent = StubAgent("finance", KB)
        ticket = {"id": "F1", "title": "Expense reimbursement", "description": "my expense report reimbursement is late", "requester": "Jo"}
        intake = agent.intake({"ticket": ticket})
        self.assertEqual(intake["status"], "awaiting_user")
        self.assertIn("expense", intake["chat"][0]["content"].lower())
        finish = agent.finish({"ticket": ticket, "last_user_reply": "Submitted in Concur two weeks ago, $240"})
        self.assertEqual((finish["status"], finish["escalation"]["to"]), ("escalated", "Finance Ops"))
        self.assertTrue(finish["chat"][0]["content"])


if __name__ == "__main__":
    unittest.main()
