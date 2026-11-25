"""Approval tokens bound to the exact draft hash. Any edit changes the hash and voids the token."""

from __future__ import annotations

import hashlib
import hmac
from uuid import UUID


def issue_token(draft_hash: str, reviewer_id: UUID, secret: bytes) -> str:
    msg = f"{draft_hash}:{reviewer_id}".encode()
    return f"{reviewer_id}.{hmac.new(secret, msg, hashlib.sha256).hexdigest()}"


def verify_token(token: str, draft_hash: str, secret: bytes) -> bool:
    reviewer, _, _sig = token.partition(".")
    try:
        expected = issue_token(draft_hash, UUID(reviewer), secret)
    except ValueError:
        return False
    return hmac.compare_digest(token, expected)
