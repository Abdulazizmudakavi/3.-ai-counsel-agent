"""Policy engine routing (Abdul). Code, not model confidence, decides where each email goes."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from counsel.contracts.analysis_record import AnalysisDraftRecord
from counsel.contracts.common import Category, RiskLevel
from counsel.contracts.email_record import EmailRecord
from counsel.gateway.stub import GatewayResult

# Categories allowed to auto-answer at L2. Empty for the whole prototype (L0).
L2_ALLOW_LIST: frozenset[Category] = frozenset()


class Route(StrEnum):
    QUARANTINE = "quarantine"
    AUTO_ANSWER = "auto_answer"
    DELEGATE_REVIEW = "delegate_review"
    LAWYER_REVIEW = "lawyer_review"
    ESCALATE = "escalate"
    ARCHIVE = "archive"
    ASSIGN_DEPARTMENT = "assign_department"


@dataclass(frozen=True)
class RoutingDecision:
    route: Route
    reasons: list[str] = field(default_factory=list)


def _domain(address: str) -> str:
    return address.rsplit("@", 1)[-1].lower()


def route(
    *,
    gateway: GatewayResult,
    email: EmailRecord | None,
    analysis: AnalysisDraftRecord | None,
    department: str | None,
    participants: set[str],
    company_domains: set[str],
) -> RoutingDecision:
    if not gateway.passed:
        return RoutingDecision(Route.QUARANTINE, gateway.reasons)
    assert email is not None

    if not email.is_legal:
        if department:
            return RoutingDecision(Route.ASSIGN_DEPARTMENT, [f"department: {department}"])
        return RoutingDecision(Route.ARCHIVE, [email.is_legal_reason])

    if (
        email.escalation_triggers
        or email.urgency is RiskLevel.CRITICAL
        or (analysis is not None and analysis.risk_level is RiskLevel.CRITICAL)
    ):
        return RoutingDecision(
            Route.ESCALATE,
            [f"trigger {t.rule_id}" for t in email.escalation_triggers] or ["risk CRITICAL"],
        )

    assert analysis is not None
    reasons: list[str] = []
    if not analysis.sendable:
        reasons.append("verifier did not pass every claim")
    if analysis.draft_reply and not {a.lower() for a in analysis.draft_reply.to} <= participants:
        reasons.append("draft adds recipients outside the thread")
    external = _domain(email.sender.email or "") not in company_domains
    if external:
        reasons.append("external sender")
    if analysis.risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH):
        reasons.append(f"risk {analysis.risk_level}")
    if email.category is not Category.COMPLIANCE:
        reasons.append(f"legal interpretation ({email.category})")
    if reasons:
        return RoutingDecision(Route.LAWYER_REVIEW, reasons)

    if email.category in L2_ALLOW_LIST:
        return RoutingDecision(Route.AUTO_ANSWER, ["L2 allow-list"])
    return RoutingDecision(Route.DELEGATE_REVIEW, ["internal, LOW risk, fully cited policy answer"])
