"""End-to-end stub flow through the HTTP API: every sample lands on its expected route."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from counsel.api.main import app
from counsel.api.samples import SAMPLES
from counsel.api.stub_routes import get_pipeline
from counsel.pipeline import DEMO_DELEGATE_ID, DEMO_LAWYER_ID, DEMO_OUTSIDER_ID

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean() -> Iterator[None]:
    get_pipeline().reset()
    yield


def run(name: str) -> dict[str, Any]:
    r = client.post(f"/stub/samples/{name}")
    assert r.status_code == 200, r.text
    return r.json()  # type: ignore[no-any-return]


def decide(item_id: str, **body: Any) -> Any:
    return client.post(f"/stub/items/{item_id}/decision", json=body)


@pytest.mark.parametrize(
    ("sample", "route", "status"),
    [
        ("nda_external", "lawyer_review", "pending"),
        ("policy_question_internal", "delegate_review", "pending"),
        ("show_cause_hindi", "escalate", "escalated"),
        ("legal_threat_customer", "escalate", "escalated"),
        ("invoice_query", "assign_department", "closed"),
        ("newsletter", "archive", "closed"),
        ("prompt_injection", "quarantine", "pending"),
    ],
)
def test_every_sample_routes_as_expected(sample: str, route: str, status: str) -> None:
    item = run(sample)
    assert item["route"] == route
    assert item["status"] == status


def test_samples_cover_every_listed_case() -> None:
    assert set(client.get("/stub/samples").json()) == set(SAMPLES)


def test_nda_flow_edit_then_approve_never_sends() -> None:
    item = run("nda_external")
    analysis = item["analysis"]
    assert analysis["risk_points"] == 8
    assert analysis["interpretation"][0]["citations"][0]["chunk_id"].startswith("stub-")
    assert "external sender" in item["reasons"]

    edited = decide(
        item["item_id"],
        reviewer_id=str(DEMO_LAWYER_ID),
        action="edit",
        edited_body="We propose a 3-year term.",
    ).json()
    assert edited["analysis"]["draft_hash"] != analysis["draft_hash"]
    assert edited["status"] == "pending"

    approved = decide(item["item_id"], reviewer_id=str(DEMO_LAWYER_ID), action="approve").json()
    assert approved["status"] == "approved_not_sent"
    assert approved["approval_token"] == "present"
    assert "disabled" in approved["history"][-1]["send"]

    again = decide(item["item_id"], reviewer_id=str(DEMO_LAWYER_ID), action="approve")
    assert again.status_code == 409


def test_matter_created_with_deadline_computed_by_code() -> None:
    item = run("nda_external")
    matter = client.get(f"/stub/matters/{item['matter_id']}").json()
    assert matter["status"] == "open"
    assert matter["deadlines"][0]["basis"] == "7 days from receipt"
    assert matter["deadlines"][0]["computed_date"]


def test_hindi_notice_escalates_without_draft() -> None:
    item = run("show_cause_hindi")
    assert item["analysis"]["draft_reply"] is None
    assert item["analysis"]["risk_level"] == "CRITICAL"
    rec = client.get(f"/stub/emails/{item['message_id']}").json()
    assert rec["language"]["code"] == "hi"
    assert rec["escalation_triggers"][0]["rule_id"] == "hi-show-cause"
    matter = client.get(f"/stub/matters/{item['matter_id']}").json()
    assert matter["legal_hold"] is True
    assert (
        decide(item["item_id"], reviewer_id=str(DEMO_LAWYER_ID), action="approve").status_code
        == 409
    )


def test_reviewer_must_be_on_access_list() -> None:
    item = run("nda_external")
    r = decide(item["item_id"], reviewer_id=str(DEMO_OUTSIDER_ID), action="approve")
    assert r.status_code == 403
    r = decide(item["item_id"], reviewer_id=str(DEMO_DELEGATE_ID), action="approve")
    assert r.status_code == 403  # delegate only sees policy matters


def test_delegate_can_approve_policy_answer() -> None:
    item = run("policy_question_internal")
    r = decide(item["item_id"], reviewer_id=str(DEMO_DELEGATE_ID), action="approve")
    assert r.json()["status"] == "approved_not_sent"


def test_reject_needs_reason() -> None:
    item = run("nda_external")
    assert (
        decide(item["item_id"], reviewer_id=str(DEMO_LAWYER_ID), action="reject").status_code == 422
    )
    r = decide(
        item["item_id"], reviewer_id=str(DEMO_LAWYER_ID), action="reject", reason="wrong playbook"
    )
    assert r.json()["status"] == "rejected"


def test_reply_in_same_thread_links_to_same_matter() -> None:
    first = run("nda_external")
    body = {
        **SAMPLES["nda_external"],
        "thread_id": first["message_id"],
        "body": "Following up on the NDA.",
    }
    second = client.post("/stub/emails", json=body).json()
    assert second["matter_id"] == first["matter_id"]
    matter = client.get(f"/stub/matters/{first['matter_id']}").json()
    assert len(matter["linked_message_ids"]) == 2


def test_audit_trail_records_each_step() -> None:
    item = run("nda_external")
    decide(item["item_id"], reviewer_id=str(DEMO_LAWYER_ID), action="approve")
    actions = [e["action"] for e in client.get("/stub/audit").json()]
    assert actions == [
        "email.received",
        "email.screened",
        "email.triaged",
        "matter.created",
        "analysis.created",
        "email.routed",
        "review.approve",
    ]


def test_unknown_fields_rejected() -> None:
    body = {**SAMPLES["newsletter"], "bcc": ["spy@x.example"]}
    assert client.post("/stub/emails", json=body).status_code == 422
