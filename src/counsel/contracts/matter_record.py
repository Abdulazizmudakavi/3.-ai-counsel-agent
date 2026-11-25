"""Matter record: created by Sana's stage, updated by all stages."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from counsel.contracts.common import (
    SCHEMA_VERSION,
    Category,
    Deadline,
    IndianState,
    Party,
    RiskLevel,
    Strict,
)

MatterStatus = Literal["open", "awaiting_counterparty", "awaiting_internal", "escalated", "closed"]


class Decision(Strict):
    summary: str = Field(min_length=1)
    decided_by: UUID
    decided_at: datetime


class MatterRecord(Strict):
    schema_version: Literal["1.0"] = SCHEMA_VERSION
    matter_id: UUID
    tenant_id: UUID
    title: str = Field(min_length=1)
    type: Category
    parties: list[Party] = Field(default_factory=list)
    states: list[IndianState] = Field(
        default_factory=list,
        description="Establishment, employee workplace, place of execution, counterparty location",
    )
    risk_level: RiskLevel
    status: MatterStatus
    deadlines: list[Deadline] = Field(default_factory=list)
    linked_message_ids: list[str] = Field(default_factory=list)
    linked_document_ids: list[UUID] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    assigned_lawyer_id: UUID | None = None
    access_list: list[UUID] = Field(min_length=1, description="User IDs allowed to see this matter")
    legal_hold: bool = False
