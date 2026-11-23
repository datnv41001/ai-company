"""Deterministic campaign planning skeleton. No LLM is invoked here."""

WORKFLOW_STEPS = [
    ("intake", "Complete client discovery and validate brief", "ai-account-director", "Approved client brief with explicit missing-information list"),
    ("research", "Research market, customer segments and competitors", "ai-market-researcher", "Source-linked research and evidence log"),
    ("strategy", "Propose positioning, channels, KPI and campaign strategy", "ai-marketing-strategist", "Campaign strategy proposal with assumptions"),
    ("content", "Build channel-specific content calendar and drafts", "ai-copywriter-content-strategist", "Editorial calendar and editable content drafts"),
    ("creative", "Prepare creative briefs and design asset plan", "ai-creative-director", "Creative brief and asset checklist"),
    ("quality", "Validate claims, brand voice, permissions and risks", "ai-content-qa", "QA findings and approval-ready assets"),
    ("reporting", "Define measurable reporting and data requirements", "ai-marketing-data-analyst", "KPI measurement plan and data-source mapping"),
]
