"""Canonical hash of a draft.

Approval tokens are bound to this hash, so the exact approved text is what gets sent.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from counsel.contracts.analysis_record import DraftReply


def compute_draft_hash(draft: DraftReply) -> str:
    canonical = json.dumps(
        draft.model_dump(mode="json"), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
