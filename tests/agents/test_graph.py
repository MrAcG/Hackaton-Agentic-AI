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

    def triage(self, tid, answer):
        view = self.svc.get_ticket(tid)
        self.assertTrue(view["awaiting_user"], "expected orchestrator triage wait")
        return self.svc.send_message(tid, answer)

    def test_vpn_pause_resume_resolve(self):
        view = self.svc.start_ticket(self.ticket("N1", "VPN down", "VPN keeps disconnecting from home"))
        self.assertTrue(view["awaiting_user"])
        view = self.triage("N1", "It's my VPN / GlobalProtect from home, auth keeps failing")
        self.assertEqual(view["team"], "network")
        self.assertTrue(view["awaiting_user"])
        self.assertIn("MFA", view["question"])
        view = self.svc.send_message("N1", "Done, it works now")
        self.assertEqual(view["status"], "resolved")
        self.assertFalse(view["awaiting_user"])

    def test_fix_fails_escalates(self):
        self.svc.start_ticket(self.ticket("N2", "Slow wifi", "wifi slow, calls freezing"))
        view = self.triage("N2", "Office Wi-Fi is slow and calls freeze")
        self.assertEqual(view["team"], "network")
        view = self.svc.send_message("N2", "no, still slow")
        self.assertEqual((view["status"], view["escalation"]["to"]), ("escalated", "Network L2"))

    def test_outage_escalates_immediately(self):
        self.svc.start_ticket(self.ticket("N3", "No network", "whole office is down"))
        view = self.triage("N3", "Whole office network outage, nobody can connect")
        self.assertEqual(view["team"], "network")
        self.assertEqual(view["status"], "escalated")
        self.assertFalse(view["awaiting_user"])

    def test_clarify_then_fix(self):
        # Triage routes to Network without naming VPN, so the specialist still clarifies.
        self.svc.start_ticket(self.ticket("N4", "Connection weird", "something is off with my connection"))
        view = self.triage("N4", "Network connectivity — sites load oddly, not sure why")
        self.assertEqual(view["team"], "network")
        self.assertEqual(view["status"], "awaiting_user")
        view = self.svc.send_message("N4", "I am at home on the vpn")
        self.assertEqual(view["findings"]["root_cause"], "vpn_auth_expired")
        self.assertTrue(view["awaiting_user"])
        view = self.svc.send_message("N4", "yes that fixed it")
        self.assertEqual(view["status"], "resolved")

    def test_unclear_reply_asks_again(self):
        self.svc.start_ticket(self.ticket("N5", "DNS", "intranet server not found"))
        view = self.triage("N5", "DNS / intranet sites won't resolve on the corp network")
        self.assertEqual(view["team"], "network")
        view = self.svc.send_message("N5", "hmm")
        self.assertTrue(view["awaiting_user"])
        self.assertIn("yes/no", view["question"].replace(" ", ""))
        view = self.svc.send_message("N5", "yes works")
        self.assertEqual(view["status"], "resolved")

    def test_finance_stub(self):
        self.svc.start_ticket(self.ticket("F1", "Reimbursement late", "expense reimbursement not received"))
        view = self.triage("F1", "Finance / expense reimbursement in Concur")
        self.assertEqual(view["team"], "finance")
        self.assertTrue(view["awaiting_user"])
        view = self.svc.send_message("F1", "Submitted in Concur two weeks ago for $240")
        self.assertEqual((view["team"], view["status"]), ("finance", "escalated"))

    def test_identity_team_intake(self):
        self.svc.start_ticket(self.ticket("I1", "Can't sign in", "password expired and MFA loops"))
        view = self.triage("I1", "Login / MFA / password — account seems locked")
        self.assertEqual(view["team"], "identity")
        self.assertTrue(view["awaiting_user"])
        self.assertIn("Identity", view["chat"][-1]["content"])
        view = self.svc.send_message("I1", "SSO to email, MFA never completes")
        self.assertEqual(view["status"], "escalated")
        self.assertEqual(view["escalation"]["to"], "Identity & Access")

    def test_tickets_are_isolated_sessions(self):
        self.svc.start_ticket(self.ticket("A", "VPN", "vpn down"))
        self.svc.start_ticket(self.ticket("B", "Wifi", "wifi slow"))
        self.triage("A", "VPN from home")
        self.triage("B", "Office wifi slow")
        self.assertEqual(self.svc.send_message("A", "works").get("status"), "resolved")
        self.assertEqual(self.svc.get_ticket("B")["status"], "awaiting_user")

    def test_errors(self):
        from backend.agents.service import TicketAlreadyStarted, TicketNotAwaitingUser, TicketNotFound

        self.svc.start_ticket(self.ticket("E1", "No network", "whole office is down"))
        with self.assertRaises(TicketAlreadyStarted):
            self.svc.start_ticket(self.ticket("E1", "x", "y"))
        # After triage, outage escalates and is not awaiting.
        self.triage("E1", "whole office outage")
        with self.assertRaises(TicketNotAwaitingUser):
            self.svc.send_message("E1", "hello")
        with self.assertRaises(TicketNotFound):
            self.svc.get_ticket("nope")


if __name__ == "__main__":
    unittest.main()
