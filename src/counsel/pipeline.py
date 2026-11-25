"""End-to-end STUB pipeline with an in-memory store.

ingest -> gateway -> triage -> matter -> analysis -> policy route -> review queue -> decision.
Every step writes an audit event. Swap each stub for the real stage as it lands; the records
between stages stay the same. Nothing here touches the database or sends mail.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4, uuid5

from counsel.agent.stub import analyse
from counsel.contracts.analysis_record import AnalysisDraftRecord, DraftReply
from counsel.contracts.common import Category, RiskLevel
from counsel.contracts.email_record import EmailRecord
from counsel.contracts.hashing import compute_draft_hash
from counsel.contracts.matter_record import MatterRecord
from counsel.gateway.stub import screen
from counsel.ingest.models import InboundEmail
from counsel.policy.approval import issue_token, verify_token
from counsel.policy.router import Route, RoutingDecision, route
from counsel.policy.sender import SendDisabledError, send_approved_draft
from counsel.triage.stub import triage

NS = UUID("6f1c2a7e-0000-4000-8000-000000000000")
DEMO_TENANT_ID = uuid5(NS, "tenant:design-partner")
DEMO_LAWYER_ID = uuid5(NS, "user:responsible-lawyer")
DEMO_DELEGATE_ID = uuid5(NS, "user:hr-legal-delegate")
DEMO_OUTSIDER_ID = uuid5(NS, "user:outsider")

ItemStatus = Literal["pending", "approved_not_sent", "rejected", "escalated", "closed"]
Action = Literal["approve", "edit", "reject", "escalate"]


class DecisionError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class ReviewItem:
    item_id: UUID
    message_id: str
    matter_id: UUID | None
    route: Route
    reasons: list[str]
    analysis: AnalysisDraftRecord | None
    status: ItemStatus = "pending"
    approval_token: str | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AuditEvent:
    id: int
    occurred_at: datetime
    actor: str
    action: str
    matter_id: UUID | None
    payload: dict[str, Any]


class StubPipeline:
    def __init__(self, company_domains: set[str], approval_secret: bytes) -> None:
        self.company_domains = company_domains
        self._secret = approval_secret
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        self.emails: dict[str, EmailRecord] = {}
        self.matters: dict[UUID, MatterRecord] = {}
        self.thread_to_matter: dict[str, UUID] = {}
        self.items: dict[UUID, ReviewItem] = {}
        self.audit: list[AuditEvent] = []

    # ------------------------------------------------------------------ helpers

    def _log(self, actor: str, action: str, matter_id: UUID | None = None, **payload: Any) -> None:
        self.audit.append(
            AuditEvent(len(self.audit) + 1, datetime.now(UTC), actor, action, matter_id, payload)
        )

    def _matter_for(self, rec: EmailRecord, subject: str) -> MatterRecord:
        existing = self.thread_to_matter.get(rec.thread_id)
        if existing:
            old = self.matters[existing]
            merged = old.model_dump(mode="json")
            merged["linked_message_ids"] = [*old.linked_message_ids, rec.message_id]
            matter = MatterRecord.model_validate(merged, strict=False)
            self._log("pipeline", "matter.linked", matter.matter_id, message_id=rec.message_id)
        else:
            access = [DEMO_LAWYER_ID]
            if rec.category is Category.COMPLIANCE:
                access.append(DEMO_DELEGATE_ID)
            matter = MatterRecord(
                matter_id=uuid4(),
                tenant_id=rec.tenant_id,
                title=subject or f"{rec.category} from {rec.sender.name}",
                type=rec.category or Category.GENERAL_INQUIRY,
                parties=[rec.sender],
                risk_level=rec.urgency,
                status="escalated" if rec.urgency is RiskLevel.CRITICAL else "open",
                deadlines=list(rec.deadlines),
                linked_message_ids=[rec.message_id],
                assigned_lawyer_id=DEMO_LAWYER_ID,
                access_list=access,
                legal_hold=rec.urgency is RiskLevel.CRITICAL,
            )
            self.thread_to_matter[rec.thread_id] = matter.matter_id
            self._log("pipeline", "matter.created", matter.matter_id, message_id=rec.message_id)
        self.matters[matter.matter_id] = matter
        return matter

    # ------------------------------------------------------------------ flow

    def process(self, email: InboundEmail) -> ReviewItem:
        with self._lock:
            self._log(
                "ingest", "email.received", message_id=email.message_id, sender=email.sender_email
            )
            gate = screen(email)
            self._log("gateway", "email.screened", passed=gate.passed, reasons=gate.reasons)

            rec: EmailRecord | None = None
            analysis: AnalysisDraftRecord | None = None
            department: str | None = None
            matter: MatterRecord | None = None
            if gate.passed:
                result = triage(email, DEMO_TENANT_ID)
                rec, department = result.record, result.department
                self.emails[rec.message_id] = rec
                self._log(
                    "triage",
                    "email.triaged",
                    category=str(rec.category),
                    urgency=str(rec.urgency),
                    language=rec.language.code,
                    triggers=[t.rule_id for t in rec.escalation_triggers],
                )
                if rec.is_legal:
                    matter = self._matter_for(rec, email.subject)
                    analysis = analyse(rec, matter, email.text)
                    self._log(
                        "agent",
                        "analysis.created",
                        matter.matter_id,
                        risk=str(analysis.risk_level),
                        draft_hash=analysis.draft_hash,
                    )

            decision: RoutingDecision = route(
                gateway=gate,
                email=rec,
                analysis=analysis,
                department=department,
                participants=email.participants,
                company_domains=self.company_domains,
            )
            item = ReviewItem(
                item_id=uuid4(),
                message_id=email.message_id,
                matter_id=matter.matter_id if matter else None,
                route=decision.route,
                reasons=decision.reasons,
                analysis=analysis,
                status="escalated"
                if decision.route is Route.ESCALATE
                else "pending"
                if decision.route in (Route.LAWYER_REVIEW, Route.DELEGATE_REVIEW, Route.QUARANTINE)
                else "closed",
            )
            self.items[item.item_id] = item
            self._log(
                "policy",
                "email.routed",
                item.matter_id,
                route=str(decision.route),
                reasons=decision.reasons,
                item_id=str(item.item_id),
            )
            if decision.route is Route.ESCALATE:
                self._log(
                    "policy",
                    "alert.sent (stub)",
                    item.matter_id,
                    to=["responsible lawyer", "design partner contact"],
                )
            return item

    def decide(
        self,
        item_id: UUID,
        *,
        reviewer_id: UUID,
        action: Action,
        reason: str | None = None,
        edited_body: str | None = None,
    ) -> ReviewItem:
        with self._lock:
            item = self.items.get(item_id)
            if item is None:
                raise DecisionError(404, "review item not found")
            matter = self.matters.get(item.matter_id) if item.matter_id else None
            if matter is None or reviewer_id not in matter.access_list:
                raise DecisionError(403, "reviewer is not on this matter's access list")
            if item.status != "pending":
                raise DecisionError(409, f"item is {item.status}, not pending")
            analysis = item.analysis
            entry: dict[str, Any] = {
                "at": datetime.now(UTC).isoformat(),
                "action": action,
                "reviewer_id": str(reviewer_id),
                "reason": reason,
            }

            if action == "reject":
                if not reason:
                    raise DecisionError(422, "a reason is required to reject")
                item.status = "rejected"
            elif action == "escalate":
                item.status = "escalated"
            elif action == "edit":
                if analysis is None or analysis.draft_reply is None or not edited_body:
                    raise DecisionError(422, "edit needs an existing draft and edited_body")
                old_hash = analysis.draft_hash
                new_reply = DraftReply(**{**analysis.draft_reply.model_dump(), "body": edited_body})
                data = analysis.model_dump()
                data.update(draft_reply=new_reply, draft_hash=compute_draft_hash(new_reply))
                item.analysis = AnalysisDraftRecord.model_validate(data, strict=False)
                item.approval_token = None  # any edit voids approval
                entry.update(
                    old_hash=old_hash,
                    new_hash=item.analysis.draft_hash,
                    old_body=analysis.draft_reply.body,
                    new_body=edited_body,
                )
            else:  # approve
                if analysis is None or analysis.draft_reply is None or analysis.draft_hash is None:
                    raise DecisionError(409, "nothing to approve: no draft reply")
                token = issue_token(analysis.draft_hash, reviewer_id, self._secret)
                assert verify_token(token, analysis.draft_hash, self._secret)
                item.approval_token = token
                try:
                    send_approved_draft(analysis.draft_reply, token)
                except SendDisabledError as exc:
                    entry["send"] = str(exc)
                item.status = "approved_not_sent"
                entry["draft_hash"] = analysis.draft_hash

            item.history.append(entry)
            self._log(
                f"user:{reviewer_id}",
                f"review.{action}",
                item.matter_id,
                item_id=str(item_id),
                status=item.status,
            )
            return item
