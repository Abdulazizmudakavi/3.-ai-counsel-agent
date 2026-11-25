from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from counsel.api.main import app
from counsel.contracts import DraftReply
from counsel.policy import sender


def test_send_is_hard_disabled() -> None:
    assert sender.SEND_ENABLED is False
    d = DraftReply.model_validate_json(
        json.dumps({"subject": "s", "body": "b", "language": "en", "to": ["a@b.example"]})
    )
    with pytest.raises(sender.SendDisabledError):
        sender.send_approved_draft(d, approval_token="anything")


def test_health_reports_send_disabled() -> None:
    body = TestClient(app).get("/health").json()
    assert body["status"] == "ok"
    assert body["send_enabled"] is False
