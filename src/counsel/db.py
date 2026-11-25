"""Database helpers. Every request runs as a scoped identity so row-level security applies."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import psycopg


@contextmanager
def user_scope(conn: psycopg.Connection, tenant_id: UUID, user_id: UUID) -> Iterator[None]:
    """Run queries as a console/agent user: sees only matters on their access list."""
    with conn.transaction():
        conn.execute("SET LOCAL ROLE counsel_app")
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))
        conn.execute("SELECT set_config('app.user_id', %s, true)", (str(user_id),))
        yield


@contextmanager
def pipeline_scope(conn: psycopg.Connection, tenant_id: UUID) -> Iterator[None]:
    """Run queries as the ingestion/triage pipeline: whole tenant, no other tenant."""
    with conn.transaction():
        conn.execute("SET LOCAL ROLE counsel_pipeline")
        conn.execute("SELECT set_config('app.tenant_id', %s, true)", (str(tenant_id),))
        yield
