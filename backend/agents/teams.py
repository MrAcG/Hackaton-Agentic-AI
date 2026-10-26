"""Enterprise-style support teams used by the orchestrator and specialists."""

from __future__ import annotations

# Internal ids used in LangGraph / classifier.
TEAMS = (
    "network",
    "endpoint",
    "identity",
    "application",
    "collaboration",
    "security",
    "finance",
    "hr",
)

# Portal assignment group labels.
TEAM_LABEL = {
    "network": "Network",
    "endpoint": "Endpoint",
    "identity": "Identity",
    "application": "Application",
    "collaboration": "Collaboration",
    "security": "Security",
    "finance": "Finance",
    "hr": "HR Ops",
}

TEAM_QUEUE = {
    "network": "Network L2",
    "endpoint": "Endpoint / Desktop Support",
    "identity": "Identity & Access",
    "application": "Application Support",
    "collaboration": "Collaboration / Messaging",
    "security": "Security Operations",
    "finance": "Finance Ops",
    "hr": "HR Operations",
}

TEAM_CATEGORY = {
    "network": "Network / Connectivity",
    "endpoint": "Endpoint / Hardware",
    "identity": "Identity & Access",
    "application": "Business Applications",
    "collaboration": "Email & Collaboration",
    "security": "Security",
    "finance": "Finance / Policy",
    "hr": "HR / People",
}

# Clarifying questions each specialist asks after it owns the ticket.
TEAM_INTAKE = {
    "network": (
        "I'm the Network specialist. To diagnose this:\n"
        "1. What fails — VPN, Wi-Fi, a specific site/app, or everything?\n"
        "2. Any exact error message?\n"
        "3. Office, home (VPN), or hotspot?\n"
        "4. When did it start, and did anything change?"
    ),
    "endpoint": (
        "I'm the Endpoint / Desktop specialist. Please share:\n"
        "1. Device type (laptop/desktop) and OS if you know it?\n"
        "2. Is it power, boot, performance, printer, or peripheral?\n"
        "3. Any recent update, drop, or docking-station change?\n"
        "4. Error codes or what you see on screen?"
    ),
    "identity": (
        "I'm the Identity & Access specialist. Please share:\n"
        "1. Is this login, MFA, password reset, or access to a system?\n"
        "2. Which app or resource (SSO, VPN, email, NetSuite, etc.)?\n"
        "3. Exact error (locked, expired, denied)?\n"
        "4. Did this ever work on this device?"
    ),
    "application": (
        "I'm the Application Support specialist. Please share:\n"
        "1. Which business application (NetSuite, Salesforce, custom app)?\n"
        "2. What were you trying to do when it failed?\n"
        "3. Exact error or screenshot description?\n"
        "4. Only you affected, or coworkers too?"
    ),
    "collaboration": (
        "I'm the Collaboration / Messaging specialist. Please share:\n"
        "1. Outlook, Teams, SharePoint, OneDrive, or something else?\n"
        "2. Send/receive, crash, sync, or meeting/audio issue?\n"
        "3. Desktop app, web, or mobile?\n"
        "4. Any recent Outlook/Teams update?"
    ),
    "security": (
        "I'm with Security Operations. Please share:\n"
        "1. Phishing email, suspicious link, malware alert, or account takeover concern?\n"
        "2. Did you click anything or enter credentials?\n"
        "3. When did you notice it?\n"
        "4. Any alert text or sender address you can paste?"
    ),
    "finance": (
        "I'm the Finance Ops specialist. Please share:\n"
        "1. Expense, invoice, reimbursement, PO, or payroll?\n"
        "2. Amount / vendor / report id if you have them?\n"
        "3. Which system (e.g. Concur) and when submitted?\n"
        "4. Any rejection or error message?"
    ),
    "hr": (
        "I'm the HR Ops specialist. Please share:\n"
        "1. Onboarding, benefits, time-off, policy, or manager change?\n"
        "2. Your location / employment type if relevant?\n"
        "3. What outcome do you need?\n"
        "4. Any deadlines?"
    ),
}

ORCHESTRATOR_INTAKE = (
    "Thanks — I'm the triage assistant. Before I assign a specialist team, I need a bit more context "
    "(answer in plain language; bullets are fine):\n\n"
    "1. What are you trying to do that isn't working?\n"
    "2. Any error message or what you see on screen?\n"
    "3. Which area feels closest?\n"
    "   • Network / VPN / Wi-Fi / can't reach sites\n"
    "   • Laptop, printer, or hardware\n"
    "   • Login, password, MFA, or access request\n"
    "   • A business app (NetSuite, Salesforce, etc.)\n"
    "   • Email, Teams, SharePoint, meetings\n"
    "   • Security / phishing / suspicious activity\n"
    "   • Expense, invoice, or finance\n"
    "   • HR / onboarding / benefits / policy\n"
    "4. When did this start?\n\n"
    "I'll route you to the right team AI, which will ask follow-ups using that team's runbooks."
)
