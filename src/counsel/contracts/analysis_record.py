"""Analysis-and-draft record: produced by Arina's stage.

Consumed by Abdul's policy engine and review console.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from counsel.contracts.common import (
    SCHEMA_VERSION,
    Fact,
    LanguageCode,
    RiskLevel,
    Sha256Hex,
    Strict,
)
from counsel.contracts.hashing import compute_draft_hash


class Citation(Strict):
    chunk_id: str = Field(min_length=1)
    heading_path: str = Field(min_length=1, description='e.g. "MSA > 9 Liability > 9.2"')
    quote: str = Field(min_length=1)


class Claim(Strict):
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1, description="Every legal statement is cited")


class VerifierResult(Strict):
    claim_id: str
    citation_resolved: bool = Field(description="Cited text exists in the retrieved source")
    supported: bool = Field(description="Source supports the claim (independent check)")
    note: str | None = None

    @property
    def passed(self) -> bool:
        return self.citation_resolved and self.supported


FindingKind = Literal[
    "preferred",
    "within_fallback",
    "beyond_walk_away",
    "missing_required",
    "unlimited_liability",
    "foreign_governing_law",
    "ambiguity",
]


class RiskFinding(Strict):
    clause_ref: str = Field(min_length=1)
    finding: FindingKind
    points: int = Field(ge=0, description="From the lawyer-owned rules table, not the model")
    evidence: str = Field(min_length=1)


class DraftReply(Strict):
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)
    language: LanguageCode
    to: list[str] = Field(
        min_length=1, description="Policy engine checks these are thread participants"
    )


class AnalysisDraftRecord(Strict):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    tenant_id: UUID
    matter_id: UUID
    message_id: str = Field(min_length=1)

    facts: list[Fact] = Field(default_factory=list)
    interpretation: list[Claim] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    recommendation: str = Field(min_length=1)

    verifier_results: list[VerifierResult] = Field(default_factory=list)
    risk_findings: list[RiskFinding] = Field(default_factory=list)
    risk_points: int = Field(ge=0)
    risk_level: RiskLevel

    draft_reply: DraftReply | None = Field(
        default=None, description="Empty for CRITICAL matters: brief for counsel only"
    )
    internal_note: str = Field(min_length=1)
    draft_hash: Sha256Hex | None = None

    model_ids: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _points_add_up(self) -> AnalysisDraftRecord:
        total = sum(f.points for f in self.risk_findings)
        if total != self.risk_points:
            raise ValueError(f"risk_points {self.risk_points} != sum of findings {total}")
        return self

    @model_validator(mode="after")
    def _every_claim_verified(self) -> AnalysisDraftRecord:
        claim_ids = {c.claim_id for c in self.interpretation}
        verified_ids = {v.claim_id for v in self.verifier_results}
        missing = claim_ids - verified_ids
        if missing:
            raise ValueError(f"claims without a verifier result: {sorted(missing)}")
        return self

    @model_validator(mode="after")
    def _critical_has_no_reply(self) -> AnalysisDraftRecord:
        if self.risk_level is RiskLevel.CRITICAL and self.draft_reply is not None:
            raise ValueError("CRITICAL matters get a brief for counsel only, never a draft reply")
        return self

    @model_validator(mode="after")
    def _hash_matches_draft(self) -> AnalysisDraftRecord:
        if self.draft_reply is None:
            if self.draft_hash is not None:
                raise ValueError("draft_hash set but there is no draft_reply")
        elif self.draft_hash != compute_draft_hash(self.draft_reply):
            raise ValueError("draft_hash does not match draft_reply")
        return self

    @property
    def sendable(self) -> bool:
        """True only if every claim passed both verifier checks. Approval is still required."""
        return self.draft_reply is not None and all(v.passed for v in self.verifier_results)
