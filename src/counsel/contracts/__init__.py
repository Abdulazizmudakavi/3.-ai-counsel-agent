"""The three shared records. These are the only interfaces between the three workstreams."""

from pydantic import BaseModel

from counsel.contracts.analysis_record import AnalysisDraftRecord, DraftReply
from counsel.contracts.email_record import EmailRecord
from counsel.contracts.hashing import compute_draft_hash
from counsel.contracts.matter_record import MatterRecord

RECORDS: dict[str, type[BaseModel]] = {
    "email_record": EmailRecord,
    "matter_record": MatterRecord,
    "analysis_draft_record": AnalysisDraftRecord,
}

__all__ = [
    "RECORDS",
    "AnalysisDraftRecord",
    "DraftReply",
    "EmailRecord",
    "MatterRecord",
    "compute_draft_hash",
]
