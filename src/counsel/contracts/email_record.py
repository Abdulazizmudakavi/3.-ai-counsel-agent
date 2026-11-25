"""Email record: produced by Sana's triage stage, consumed by Arina and Abdul."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from counsel.contracts.common import (
    SCHEMA_VERSION,
    Category,
    Deadline,
    Fact,
    Intent,
    LanguageCode,
    Party,
    RiskLevel,
    Score,
    Sha256Hex,
    Signal,
    Strict,
)


class LanguageInfo(Strict):
    code: LanguageCode
    script: str | None = Field(default=None, description='ISO 15924, e.g. "Deva", "Taml", "Latn"')
    romanised: bool = Field(default=False, description="e.g. Hindi written in Latin letters")


class AttachmentInfo(Strict):
    attachment_id: str = Field(min_length=1)
    filename: str
    sha256: Sha256Hex
    language: LanguageInfo | None = None
    ocr_used: bool = False
    low_confidence_pages: list[int] = Field(
        default_factory=list, description="Pages below the OCR confidence floor; sent to a human"
    )


class TriggerHit(Strict):
    """A hit from the deterministic escalation rules (keyword / sender), not the model."""

    rule_id: str = Field(min_length=1)
    matched_text: str = Field(min_length=1)
    language: LanguageCode


class MatterCandidate(Strict):
    matter_id: UUID
    score: Score
    reasons: list[str] = Field(min_length=1)


class EmailRecord(Strict):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    tenant_id: UUID
    message_id: str = Field(min_length=1, description="RFC 5322 Message-ID")
    thread_id: str = Field(min_length=1)
    received_at: datetime
    sender: Party
    language: LanguageInfo
    attachments: list[AttachmentInfo] = Field(default_factory=list)

    is_legal: bool
    is_legal_reason: str = Field(min_length=1)
    category: Category | None = Field(default=None, description="Required when is_legal is true")
    intent: Intent
    parties: list[Party] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    deadlines: list[Deadline] = Field(default_factory=list)
    signals: list[Signal] = Field(default_factory=list)
    escalation_triggers: list[TriggerHit] = Field(default_factory=list)
    missing_info: list[str] = Field(default_factory=list)
    matter_candidates: list[MatterCandidate] = Field(default_factory=list)
    urgency: RiskLevel = Field(description="Set by rules from deadlines and signals, not the model")

    triage_model: str = Field(
        min_length=1, description="Model ID used, for the Jev vs Haiku benchmark"
    )

    @model_validator(mode="after")
    def _legal_needs_category(self) -> EmailRecord:
        if self.is_legal and self.category is None:
            raise ValueError("category is required when is_legal is true")
        if not self.is_legal and self.category is not None:
            raise ValueError("category must be empty when is_legal is false")
        return self

    @model_validator(mode="after")
    def _triggers_mean_critical(self) -> EmailRecord:
        if self.escalation_triggers and self.urgency is not RiskLevel.CRITICAL:
            raise ValueError("an escalation trigger hit requires urgency CRITICAL")
        return self
