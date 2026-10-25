"""End-to-end tests through the real LangGraph graph, including pause/resume.

Skipped automatically if langgraph isn't installed.
"""

import importlib.util
import unittest

HAS_LANGGRAPH = importlib.util.find_spec("langgraph") is not None


@unittest.skipUnless(HAS_LANGGRAPH, "langgraph not installed")
class GraphTests(unittest.TestCase):
    def setUp(self):
        from backend.agents.config import AgentSettings
        from backend.agents.service import AgentService

        self.svc = AgentService(settings=AgentSettings(), llm=None)

    def ticket(self, tid, title, description, scenario=None):
        t = {"id": tid, "title": title, "description": description, "requester": "Sam"}
        if scenario:
            t["mock_scenario"] = scenario
        return t

    def test_vpn_pause_resume_resolve(self):
        view = self.svc.start_ticket(self.ticket("N1", "VPN down", "VPN keeps disconnecting from home"))
        self.assertEqual((view["team"], view["status"], view["awaiting_user"]), ("network", "awaiting_user", True))
        self.assertIn("MFA", view["question"])
        view = self.svc.send_message("N1", "Done, it works now")
        self.assertEqual(view["status"], "resolved")
        self.assertFalse(view["awaiting_user"])
        self.assertEqual([m["role"] for m in view["chat"]], ["agent", "user", "agent"])

    def test_fix_fails_escalates(self):
        self.svc.start_ticket(self.ticket("N2", "Slow wifi", "wifi slow, calls freezing"))
        view = self.svc.send_message("N2", "no, still slow")
        self.assertEqual((view["status"], view["escalation"]["to"]), ("escalated", "Network L2"))

    def test_outage_escalates_immediately(self):
        view = self.svc.start_ticket(self.ticket("N3", "No network", "whole office is down"))
        self.assertEqual(view["status"], "escalated")
        self.assertFalse(view["awaiting_user"])

    def test_clarify_then_fix(self):
        view = self.svc.start_ticket(self.ticket("N4", "Connection weird", "something is off with my connection"))
        self.assertEqual(view["status"], "awaiting_user")
        view = self.svc.send_message("N4", "I'm working from home on the vpn")
        self.assertEqual(view["findings"]["root_cause"], "vpn_auth_expired")
        self.assertTrue(view["awaiting_user"])
        view = self.svc.send_message("N4", "yes that fixed it")
        self.assertEqual(view["status"], "resolved")

    def test_unclear_reply_asks_again(self):
        self.svc.start_ticket(self.ticket("N5", "DNS", "intranet server not found"))
        view = self.svc.send_message("N5", "hmm")
        self.assertTrue(view["awaiting_user"])
        self.assertIn("yes / no", view["question"])
        view = self.svc.send_message("N5", "yes works")
        self.assertEqual(view["status"], "resolved")

    def test_finance_stub(self):
        view = self.svc.start_ticket(self.ticket("F1", "Reimbursement late", "expense reimbursement not received"))
        self.assertEqual((view["team"], view["status"]), ("finance", "escalated"))

    def test_tickets_are_isolated_sessions(self):
        self.svc.start_ticket(self.ticket("A", "VPN", "vpn down"))
        self.svc.start_ticket(self.ticket("B", "Wifi", "wifi slow"))
        self.assertEqual(self.svc.send_message("A", "works").get("status"), "resolved")
        self.assertEqual(self.svc.get_ticket("B")["status"], "awaiting_user")

    def test_errors(self):
        from backend.agents.service import TicketAlreadyStarted, TicketNotAwaitingUser, TicketNotFound

        self.svc.start_ticket(self.ticket("E1", "No network", "whole office is down"))
        with self.assertRaises(TicketAlreadyStarted):
            self.svc.start_ticket(self.ticket("E1", "x", "y"))
        with self.assertRaises(TicketNotAwaitingUser):
            self.svc.send_message("E1", "hello")
        with self.assertRaises(TicketNotFound):
            self.svc.get_ticket("nope")


if __name__ == "__main__":
    unittest.main()
