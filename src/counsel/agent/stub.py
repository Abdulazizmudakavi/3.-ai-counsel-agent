"""STUB legal brain (Arina). Real version: Opus orchestrator, hybrid search, verifier.

Returns canned, correctly shaped analysis so the console and policy engine can be built now.
Citations point at fake chunk IDs ("stub-...") that do not exist in any knowledge base.
"""

from __future__ import annotations

import re

from counsel.contracts.analysis_record import (
    AnalysisDraftRecord,
    Citation,
    Claim,
    DraftReply,
    RiskFinding,
    VerifierResult,
)
from counsel.contracts.common import Category, RiskLevel
from counsel.contracts.email_record import EmailRecord
from counsel.contracts.hashing import compute_draft_hash
from counsel.contracts.matter_record import MatterRecord
from counsel.policy.risk import band, max_level

AGENT_MODEL = "stub-agent-v0"
NDA_MAX_TERM_YEARS = 3


def _nda(email: EmailRecord, body: str) -> tuple[list[Claim], list[RiskFinding], str]:
    term = re.search(r"(\d{1,2})[- ]?(?:\(\w+\)\s*)?years?", body, flags=re.IGNORECASE)
    years = int(term.group(1)) if term else None
    cite = Citation(
        chunk_id="stub-nda-playbook-2.1",
        heading_path="NDA Playbook > 2 Term > 2.1",
        quote=f"Preferred: up to {NDA_MAX_TERM_YEARS} years. Walk-away: above 3 years.",
    )
    if years and years > NDA_MAX_TERM_YEARS:
        claim = Claim(
            claim_id="c1",
            citations=[cite],
            text=f"The proposed {years}-year term exceeds the playbook maximum of "
            f"{NDA_MAX_TERM_YEARS} years.",
        )
        finding = RiskFinding(
            clause_ref="Term",
            finding="beyond_walk_away",
            points=8,
            evidence=term.group(0) if term else "",
        )
        reco = f"Propose a {NDA_MAX_TERM_YEARS}-year term."
    else:
        claim = Claim(
            claim_id="c1",
            citations=[cite],
            text="No term above the playbook maximum was found in the email text.",
        )
        finding = RiskFinding(
            clause_ref="Term",
            finding="preferred",
            points=0,
            evidence=term.group(0) if term else "no term stated",
        )
        reco = "Review the attached NDA in full; the email text shows no term deviation."
    return [claim], [finding], reco


def _policy() -> tuple[list[Claim], list[RiskFinding], str]:
    cite = Citation(
        chunk_id="stub-hr-policy-4.3",
        heading_path="HR Policy > 4 Leave > 4.3",
        quote="Up to 10 days of unused earned leave may be carried forward.",
    )
    claim = Claim(
        claim_id="c1",
        citations=[cite],
        text="Up to 10 days of unused earned leave can be carried forward.",
    )
    return [claim], [], "Answer from HR Policy 4.3."


def analyse(email: EmailRecord, matter: MatterRecord, body: str) -> AnalysisDraftRecord:
    sender = email.sender.email or ""
    if email.urgency is RiskLevel.CRITICAL:
        triggers = ", ".join(t.rule_id for t in email.escalation_triggers)
        return AnalysisDraftRecord(
            tenant_id=email.tenant_id,
            matter_id=matter.matter_id,
            message_id=email.message_id,
            facts=list(email.facts),
            recommendation="Escalate to the responsible lawyer now. "
            "No reply is drafted for CRITICAL matters.",
            risk_points=0,
            risk_level=RiskLevel.CRITICAL,
            internal_note=f"BRIEF FOR COUNSEL (stub). Triggers: {triggers}. "
            f"Deadlines: {[d.basis for d in email.deadlines] or 'none found'}.",
            model_ids=[AGENT_MODEL],
        )

    if email.category is Category.NDA:
        claims, findings, reco = _nda(email, body)
    elif email.category is Category.COMPLIANCE:
        claims, findings, reco = _policy()
    else:
        claims, findings, reco = [], [], "A lawyer should read this; no playbook topic matched."

    points = sum(f.points for f in findings)
    level = max_level(email.urgency, band(points))
    reply = DraftReply(
        subject=f"Re: {matter.title}",
        body="Thank you for your email. "
        + (claims[0].text if claims else "We have received your message and will respond shortly."),
        language=email.language.code,
        to=[sender],
    )
    return AnalysisDraftRecord(
        tenant_id=email.tenant_id,
        matter_id=matter.matter_id,
        message_id=email.message_id,
        facts=list(email.facts),
        interpretation=claims,
        assumptions=["Stub analysis: canned text, not legal advice."],
        recommendation=reco,
        verifier_results=[
            VerifierResult(
                claim_id=c.claim_id, citation_resolved=True, supported=True, note="stub verifier"
            )
            for c in claims
        ],
        risk_findings=findings,
        risk_points=points,
        risk_level=level,
        draft_reply=reply,
        internal_note=f"Stub draft for {email.category}.",
        draft_hash=compute_draft_hash(reply),
        model_ids=[AGENT_MODEL],
    )
