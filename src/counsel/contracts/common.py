"""Types shared by the three records.

Changing anything here needs approval from all three owners.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION: Literal["1.0"] = "1.0"

# ISO 3166-2:IN state / union territory code, e.g. "IN-MH", "IN-KA".
IndianState = Annotated[str, Field(pattern=r"^IN-[A-Z]{2}$")]
# ISO 639-1/639-3 language code, e.g. "en", "hi", "mr", "ta".
LanguageCode = Annotated[str, Field(pattern=r"^[a-z]{2,3}$")]
Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Score = Annotated[float, Field(ge=0.0, le=1.0)]


class Strict(BaseModel):
    """Base for every record.

    Unknown fields are an error, values are not coerced, objects are immutable.
    """

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class RiskLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Category(StrEnum):
    CONTRACT_REVIEW = "contract_review"
    VENDOR_DISPUTE = "vendor_dispute"
    CUSTOMER_DISPUTE = "customer_dispute"
    EMPLOYMENT = "employment"
    REGULATORY_NOTICE = "regulatory_notice"
    DATA_PRIVACY = "data_privacy"
    IP = "ip"
    NDA = "nda"
    PROCUREMENT = "procurement"
    LITIGATION_THREAT = "litigation_threat"
    PAYMENT_DISPUTE = "payment_dispute"
    COMPLIANCE = "compliance"
    CORPORATE_GOVERNANCE = "corporate_governance"
    PARTNERSHIP = "partnership"
    CONFIDENTIALITY = "confidentiality"
    GENERAL_INQUIRY = "general_inquiry"


class Intent(StrEnum):
    QUESTION = "question"
    REVIEW_REQUEST = "review_request"
    NOTICE = "notice"
    DEMAND = "demand"
    FYI = "fyi"
    SCHEDULING = "scheduling"


class Signal(StrEnum):
    DISPUTE = "dispute"
    LITIGATION_THREAT = "litigation_threat"
    REGULATOR = "regulator"
    BREACH = "breach"
    TERMINATION = "termination"
    INDEMNITY_CLAIM = "indemnity_claim"
    FRAUD = "fraud"
    CRIMINAL = "criminal"
    DATA_INCIDENT = "data_incident"


class SourceQuote(Strict):
    """An exact span from an email, attachment or document that supports a value."""

    source_id: str = Field(min_length=1, description="Message ID, attachment ID or chunk ID")
    quote: str = Field(min_length=1)


class Party(Strict):
    name: str = Field(min_length=1)
    email: str | None = None
    organisation: str | None = None
    role: Literal["sender", "recipient", "internal_requester", "counterparty", "other"]
    cin: str | None = Field(default=None, description="Company Identification Number if found")


class Fact(Strict):
    statement: str = Field(min_length=1)
    source: SourceQuote


class Deadline(Strict):
    description: str = Field(min_length=1)
    basis: str = Field(min_length=1, description='e.g. "15 days from receipt"')
    computed_date: date | None = Field(
        default=None, description="Computed by code from the basis, never by the model"
    )
    source: SourceQuote
