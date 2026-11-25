"""Append-only audit log. The database rejects UPDATE and DELETE on audit_events."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb


def write_event(
    conn: psycopg.Connection,
    *,
    tenant_id: UUID,
    actor: str,
    action: str,
    matter_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> int:
    row = conn.execute(
        """
        INSERT INTO audit_events (tenant_id, actor, action, matter_id, payload)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
        """,
        (tenant_id, actor, action, matter_id, Jsonb(payload or {})),
    ).fetchone()
    assert row is not None
    return int(row[0])
