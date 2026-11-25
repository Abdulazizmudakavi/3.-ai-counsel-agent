"""Inbound email as it arrives from the mailbox connector (or a test request in the prototype)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class InboundEmail(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    message_id: str = Field(default_factory=lambda: f"<{uuid4().hex}@stub.local>")
    thread_id: str | None = Field(default=None, description="Defaults to message_id (new thread)")
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sender_name: str = Field(min_length=1)
    sender_email: str = Field(pattern=r"^[^@\s]+@[^@\s]+$")
    to: list[str] = Field(min_length=1)
    subject: str = ""
    body: str = Field(min_length=1)

    @property
    def thread(self) -> str:
        return self.thread_id or self.message_id

    @property
    def participants(self) -> set[str]:
        return {self.sender_email.lower(), *(a.lower() for a in self.to)}

    @property
    def text(self) -> str:
        return f"{self.subject}\n{self.body}"
