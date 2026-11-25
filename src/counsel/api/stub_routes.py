"""STUB endpoints for testing the sample email flow end to end (in-memory, no sending)."""

from __future__ import annotations

from dataclasses import asdict
from functools import lru_cache
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from counsel.api.samples import SAMPLES
from counsel.config import get_settings
from counsel.contracts.email_record import EmailRecord
from counsel.contracts.matter_record import MatterRecord
from counsel.ingest.models import InboundEmail
from counsel.pipeline import (
    DEMO_DELEGATE_ID,
    DEMO_LAWYER_ID,
    DEMO_OUTSIDER_ID,
    Action,
    DecisionError,
    ReviewItem,
    StubPipeline,
)

router = APIRouter(prefix="/stub", tags=["stub flow"])


@lru_cache(maxsize=1)
def get_pipeline() -> StubPipeline:
    s = get_settings()
    return StubPipeline(
        company_domains={d.lower() for d in s.company_domains},
        approval_secret=s.approval_secret.get_secret_value().encode(),
    )


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reviewer_id: UUID
    action: Action
    reason: str | None = None
    edited_body: str | None = None


def _item(item: ReviewItem) -> dict[str, Any]:
    out = asdict(item)
    out["analysis"] = item.analysis.model_dump(mode="json") if item.analysis else None
    out["approval_token"] = "present" if item.approval_token else None  # never echo the token
    return out


@router.get("/users")
def demo_users() -> dict[str, UUID]:
    """Demo reviewer IDs to use in decisions."""
    return {
        "responsible_lawyer": DEMO_LAWYER_ID,
        "hr_legal_delegate": DEMO_DELEGATE_ID,
        "outsider": DEMO_OUTSIDER_ID,
    }


@router.get("/samples")
def list_samples() -> dict[str, dict[str, Any]]:
    return SAMPLES


@router.post("/samples/{name}")
def run_sample(name: str) -> dict[str, Any]:
    if name not in SAMPLES:
        raise HTTPException(404, f"unknown sample; choose from {sorted(SAMPLES)}")
    return _item(get_pipeline().process(InboundEmail(**SAMPLES[name])))


@router.post("/emails")
def ingest_email(email: InboundEmail) -> dict[str, Any]:
    """Run one email through gateway, triage, matter, analysis and routing."""
    return _item(get_pipeline().process(email))


@router.get("/emails/{message_id}")
def get_email(message_id: str) -> EmailRecord:
    rec = get_pipeline().emails.get(message_id)
    if rec is None:
        raise HTTPException(404, "email not found (or quarantined before triage)")
    return rec


@router.get("/matters")
def list_matters() -> list[MatterRecord]:
    return list(get_pipeline().matters.values())


@router.get("/matters/{matter_id}")
def get_matter(matter_id: UUID) -> MatterRecord:
    matter = get_pipeline().matters.get(matter_id)
    if matter is None:
        raise HTTPException(404, "matter not found")
    return matter


@router.get("/review-queue")
def review_queue(status: str = "pending") -> list[dict[str, Any]]:
    return [_item(i) for i in get_pipeline().items.values() if i.status == status]


@router.get("/items/{item_id}")
def get_item(item_id: UUID) -> dict[str, Any]:
    item = get_pipeline().items.get(item_id)
    if item is None:
        raise HTTPException(404, "item not found")
    return _item(item)


@router.post("/items/{item_id}/decision")
def decide(item_id: UUID, decision: Decision) -> dict[str, Any]:
    """approve | edit | reject | escalate. Approve issues a token; sending stays disabled."""
    try:
        item = get_pipeline().decide(
            item_id,
            reviewer_id=decision.reviewer_id,
            action=decision.action,
            reason=decision.reason,
            edited_body=decision.edited_body,
        )
    except DecisionError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    return _item(item)


@router.get("/audit")
def audit(matter_id: UUID | None = None) -> list[dict[str, Any]]:
    events = get_pipeline().audit
    return [asdict(e) for e in events if matter_id is None or e.matter_id == matter_id]


@router.post("/reset")
def reset() -> dict[str, str]:
    get_pipeline().reset()
    return {"status": "cleared"}
