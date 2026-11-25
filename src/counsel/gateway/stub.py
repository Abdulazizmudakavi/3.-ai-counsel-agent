"""STUB security gateway (Abdul). Real version: SPF/DKIM/DMARC, malware scan, injection classifier.

The stub only pattern-matches obvious prompt-injection phrases so the quarantine path can be
exercised end to end.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from counsel.ingest.models import InboundEmail

INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) instructions",
    r"disregard (your|the) (rules|instructions)",
    r"forward (all|every) (contracts?|emails?|documents?)",
    r"reveal (your )?(system prompt|instructions)",
    r"you are now (a|an|the)\b",
]


@dataclass(frozen=True)
class GatewayResult:
    passed: bool
    reasons: list[str] = field(default_factory=list)


def screen(email: InboundEmail) -> GatewayResult:
    reasons = [
        f"possible prompt injection: /{p}/"
        for p in INJECTION_PATTERNS
        if re.search(p, email.text, flags=re.IGNORECASE)
    ]
    return GatewayResult(passed=not reasons, reasons=reasons)
