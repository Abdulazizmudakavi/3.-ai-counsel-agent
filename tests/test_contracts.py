from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from counsel.contracts import (
    AnalysisDraftRecord,
    DraftReply,
    EmailRecord,
    MatterRecord,
    compute_draft_hash,
)
from scripts.export_schemas import OUT, render

TENANT = str(uuid4())
QUOTE = {"source_id": "msg-1", "quote": "Please review the attached NDA"}


def email_json(**overrides: Any) -> str:
    data: dict[str, Any] = {
        "tenant_id": TENANT,
        "message_id": "<abc@acme.example>",
        "thread_id": "t-1",
        "received_at": "2026-11-25T10:00:00+05:30",
        "sender": {"name": "Ravi", "email": "ravi@acme.example", "role": "sender"},
        "language": {"code": "hi", "script": "Deva"},
        "is_legal": True,
        "is_legal_reason": "NDA review request",
        "category": "nda",
        "intent": "review_request",
        "facts": [{"statement": "Acme sent an NDA", "source": QUOTE}],
        "urgency": "MEDIUM",
        "triage_model": "haiku-test",
    }
    data.update(overrides)
    return json.dumps(data)


def draft() -> DraftReply:
    return DraftReply.model_validate_json(
        json.dumps(
            {
                "subject": "Re: NDA",
                "body": "Please see our comments.",
                "language": "en",
                "to": ["ravi@acme.example"],
            }
        )
    )


def analysis_json(**overrides: Any) -> str:
    d = draft()
    data: dict[str, Any] = {
        "tenant_id": TENANT,
        "matter_id": str(uuid4()),
        "message_id": "<abc@acme.example>",
        "interpretation": [
            {
                "claim_id": "c1",
                "text": "Term exceeds playbook maximum of 3 years",
                "citations": [
                    {
                        "chunk_id": "ch-9",
                        "heading_path": "NDA Playbook > 2 Term > 2.1",
                        "quote": "Maximum term: 3 years",
                    }
                ],
            }
        ],
        "recommendation": "Propose a 3 year term",
        "verifier_results": [{"claim_id": "c1", "citation_resolved": True, "supported": True}],
        "risk_findings": [
            {
                "clause_ref": "cl. 7",
                "finding": "beyond_walk_away",
                "points": 8,
                "evidence": "term of five (5) years",
            }
        ],
        "risk_points": 8,
        "risk_level": "MEDIUM",
        "draft_reply": d.model_dump(mode="json"),
        "internal_note": "One deviation found",
        "draft_hash": compute_draft_hash(d),
        "model_ids": ["opus-test"],
    }
    data.update(overrides)
    return json.dumps(data)


def test_valid_email_record() -> None:
    rec = EmailRecord.model_validate_json(email_json())
    assert rec.category is not None and rec.category.value == "nda"


def test_unknown_field_rejected() -> None:
    with pytest.raises(ValidationError):
        EmailRecord.model_validate_json(email_json(surprise="x"))


def test_legal_email_needs_category() -> None:
    with pytest.raises(ValidationError, match="category is required"):
        EmailRecord.model_validate_json(email_json(category=None))


def test_trigger_forces_critical() -> None:
    hit = [{"rule_id": "kw-showcause-hi", "matched_text": "कारण बताओ नोटिस", "language": "hi"}]
    with pytest.raises(ValidationError, match="CRITICAL"):
        EmailRecord.model_validate_json(email_json(escalation_triggers=hit))
    EmailRecord.model_validate_json(email_json(escalation_triggers=hit, urgency="CRITICAL"))


def test_state_code_format() -> None:
    base = {
        "matter_id": str(uuid4()),
        "tenant_id": TENANT,
        "title": "Acme NDA",
        "type": "nda",
        "risk_level": "LOW",
        "status": "open",
        "access_list": [str(uuid4())],
    }
    MatterRecord.model_validate_json(json.dumps({**base, "states": ["IN-MH", "IN-KA"]}))
    with pytest.raises(ValidationError):
        MatterRecord.model_validate_json(json.dumps({**base, "states": ["Maharashtra"]}))


def test_valid_analysis_record() -> None:
    rec = AnalysisDraftRecord.model_validate_json(analysis_json())
    assert rec.sendable


def test_draft_hash_must_match() -> None:
    with pytest.raises(ValidationError, match="draft_hash"):
        AnalysisDraftRecord.model_validate_json(analysis_json(draft_hash="0" * 64))


def test_risk_points_must_add_up() -> None:
    with pytest.raises(ValidationError, match="risk_points"):
        AnalysisDraftRecord.model_validate_json(analysis_json(risk_points=3))


def test_every_claim_needs_verifier_result() -> None:
    with pytest.raises(ValidationError, match="verifier"):
        AnalysisDraftRecord.model_validate_json(analysis_json(verifier_results=[]))


def test_critical_gets_no_draft_reply() -> None:
    with pytest.raises(ValidationError, match="CRITICAL"):
        AnalysisDraftRecord.model_validate_json(analysis_json(risk_level="CRITICAL"))


def test_failed_verification_is_not_sendable() -> None:
    bad = [{"claim_id": "c1", "citation_resolved": True, "supported": False}]
    assert not AnalysisDraftRecord.model_validate_json(analysis_json(verifier_results=bad)).sendable


def test_published_schemas_are_up_to_date() -> None:
    for filename, text in render().items():
        path = OUT / filename
        assert path.exists(), f"run: python scripts/export_schemas.py ({filename} missing)"
        assert path.read_text(encoding="utf-8") == text, f"{filename} is stale; re-export"
