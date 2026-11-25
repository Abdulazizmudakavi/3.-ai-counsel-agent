"""STUB triage (Sana). Real version: Haiku / Jev model plus the advocate's keyword lists.

Deterministic keyword rules only, so every route can be tested. The non-English keywords are
illustrative placeholders until the advocate supplies the real lists.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from counsel.contracts.common import (
    Category,
    Deadline,
    Fact,
    Intent,
    Party,
    RiskLevel,
    Signal,
    SourceQuote,
)
from counsel.contracts.email_record import EmailRecord, LanguageInfo, TriggerHit
from counsel.ingest.models import InboundEmail

TRIAGE_MODEL = "stub-rules-v0"

# (rule_id, language, pattern, category, signal)
ESCALATION_RULES: list[tuple[str, str, str, Category, Signal]] = [
    ("en-show-cause", "en", r"show[- ]cause", Category.REGULATORY_NOTICE, Signal.REGULATOR),
    ("en-summons", "en", r"\bsummons\b", Category.LITIGATION_THREAT, Signal.LITIGATION_THREAT),
    (
        "en-legal-notice",
        "en",
        r"legal notice",
        Category.LITIGATION_THREAT,
        Signal.LITIGATION_THREAT,
    ),
    ("en-s138", "en", r"section 138", Category.PAYMENT_DISPUTE, Signal.CRIMINAL),
    ("en-breach", "en", r"data breach", Category.DATA_PRIVACY, Signal.DATA_INCIDENT),
    (
        "en-regulator",
        "en",
        r"\b(SEBI|RBI|MCA|CERT-In)\b",
        Category.REGULATORY_NOTICE,
        Signal.REGULATOR,
    ),
    (
        "en-legal-action",
        "en",
        r"legal action",
        Category.LITIGATION_THREAT,
        Signal.LITIGATION_THREAT,
    ),
    ("hi-show-cause", "hi", r"कारण बताओ", Category.REGULATORY_NOTICE, Signal.REGULATOR),
    ("hi-summons", "hi", r"समन", Category.LITIGATION_THREAT, Signal.LITIGATION_THREAT),
    ("hi-legal-notice", "hi", r"कानूनी नोटिस", Category.LITIGATION_THREAT, Signal.LITIGATION_THREAT),
    ("mr-show-cause", "mr", r"कारणे दाखवा", Category.REGULATORY_NOTICE, Signal.REGULATOR),
    (
        "mr-legal-notice",
        "mr",
        r"कायदेशीर नोटीस",
        Category.LITIGATION_THREAT,
        Signal.LITIGATION_THREAT,
    ),
    (
        "ta-legal-notice",
        "ta",
        r"சட்ட அறிவிப்பு",
        Category.LITIGATION_THREAT,
        Signal.LITIGATION_THREAT,
    ),
]

DEPARTMENT_RULES: list[tuple[str, str]] = [
    ("finance", r"\binvoice\b|payment status|reimbursement"),
    ("it", r"password|laptop|vpn|access request"),
]
ARCHIVE_PATTERN = r"unsubscribe|newsletter|out of office|automatic reply"

SCRIPTS: list[tuple[str, str, str]] = [  # (language, ISO 15924 script, unicode range)
    ("hi", "Deva", "ऀ-ॿ"),
    ("bn", "Beng", "ঀ-৿"),
    ("gu", "Gujr", "઀-૿"),
    ("ta", "Taml", "஀-௿"),
    ("te", "Telu", "ఀ-౿"),
    ("kn", "Knda", "ಀ-೿"),
]


@dataclass(frozen=True)
class TriageResult:
    record: EmailRecord
    department: str | None


def detect_language(text: str) -> LanguageInfo:
    counts = [(len(re.findall(f"[{rng}]", text)), lang, script) for lang, script, rng in SCRIPTS]
    best = max(counts)
    if best[0] >= 3:
        return LanguageInfo(code=best[1], script=best[2])
    return LanguageInfo(code="en", script="Latn")


def _quote(email: InboundEmail, text: str) -> SourceQuote:
    return SourceQuote(source_id=email.message_id, quote=text)


def _first_sentence(body: str) -> str:
    return re.split(r"(?<=[.?!।])\s", body.strip(), maxsplit=1)[0][:300]


def _deadlines(email: InboundEmail) -> list[Deadline]:
    out = []
    for m in re.finditer(r"within (\d{1,3}) days", email.body, flags=re.IGNORECASE):
        days = int(m.group(1))
        out.append(
            Deadline(
                description="Response or action deadline stated in the email",
                basis=f"{days} days from receipt",
                computed_date=(email.received_at + timedelta(days=days)).date(),  # code, not model
                source=_quote(email, m.group(0)),
            )
        )
    return out


def triage(email: InboundEmail, tenant_id: UUID) -> TriageResult:
    text = email.text
    language = detect_language(text)
    hits = [
        (TriggerHit(rule_id=rid, matched_text=m.group(0), language=lang), cat, sig)
        for rid, lang, pat, cat, sig in ESCALATION_RULES
        if (m := re.search(pat, text, flags=re.IGNORECASE))
    ]
    if hits and language.code == "hi" and any(h.language == "mr" for h, _, _ in hits):
        language = LanguageInfo(code="mr", script="Deva")

    department = next(
        (d for d, pat in DEPARTMENT_RULES if re.search(pat, text, flags=re.IGNORECASE)), None
    )
    is_archive = bool(re.search(ARCHIVE_PATTERN, text, flags=re.IGNORECASE))

    category: Category | None
    if hits:
        is_legal, category, intent = True, hits[0][1], Intent.NOTICE
        reason, urgency = f"escalation rule {hits[0][0].rule_id}", RiskLevel.CRITICAL
    elif re.search(r"\bnda\b|non-disclosure", text, flags=re.IGNORECASE):
        is_legal, category, intent = True, Category.NDA, Intent.REVIEW_REQUEST
        reason, urgency = "mentions an NDA", RiskLevel.MEDIUM
    elif re.search(r"\bpolicy\b|\bleave\b|carry forward|notice period", text, flags=re.I):
        is_legal, category, intent = True, Category.COMPLIANCE, Intent.QUESTION
        reason, urgency = "internal policy question", RiskLevel.LOW
    elif department or is_archive:
        is_legal, category, intent = False, None, Intent.FYI
        reason = f"non-legal, route to {department}" if department else "non-legal, no action"
        urgency = RiskLevel.LOW
    else:
        is_legal, category, intent = True, Category.GENERAL_INQUIRY, Intent.QUESTION
        reason, urgency = "unclassified - treated as legal so a human sees it", RiskLevel.MEDIUM

    record = EmailRecord(
        tenant_id=tenant_id,
        message_id=email.message_id,
        thread_id=email.thread,
        received_at=email.received_at,
        sender=Party(name=email.sender_name, email=email.sender_email, role="sender"),
        language=language,
        is_legal=is_legal,
        is_legal_reason=reason,
        category=category,
        intent=intent,
        facts=[
            Fact(
                statement="Opening of the email", source=_quote(email, _first_sentence(email.body))
            )
        ],
        deadlines=_deadlines(email) if is_legal else [],
        signals=sorted({sig for _, _, sig in hits}),
        escalation_triggers=[h for h, _, _ in hits],
        urgency=urgency,
        triage_model=TRIAGE_MODEL,
    )
    return TriageResult(record=record, department=None if is_legal else department)
