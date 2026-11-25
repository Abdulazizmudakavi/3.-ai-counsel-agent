"""Row-level security and audit tests. Need a Postgres with pgvector: set COUNSEL_TEST_ADMIN_URL.

The test creates a throwaway database, applies the migrations, and checks that a restricted
user gets nothing back (team plan, Abdul weeks 2-3).
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import sql

from counsel.audit.log import write_event
from counsel.db import pipeline_scope, user_scope
from scripts.migrate import migrate

ADMIN_URL = os.environ.get("COUNSEL_TEST_ADMIN_URL")
pytestmark = pytest.mark.skipif(not ADMIN_URL, reason="COUNSEL_TEST_ADMIN_URL not set")


@dataclass(frozen=True)
class World:
    conn: psycopg.Connection
    tenant: UUID
    other_tenant: UUID
    lawyer: UUID  # on the matter's access list
    outsider: UUID  # same tenant, not on the list
    requester: UUID  # same tenant, not a legal role
    matter: UUID


@pytest.fixture(scope="module")
def world() -> Iterator[World]:
    assert ADMIN_URL
    name = f"counsel_test_{uuid4().hex[:8]}"
    with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    url = psycopg.conninfo.make_conninfo(ADMIN_URL, dbname=name)
    try:
        migrate(url)
        conn = psycopg.connect(url, autocommit=True)
        t1, t2 = uuid4(), uuid4()
        lawyer, outsider, requester, other = uuid4(), uuid4(), uuid4(), uuid4()
        matter, other_matter = uuid4(), uuid4()
        conn.execute("INSERT INTO tenants (id, name) VALUES (%s,'Acme'), (%s,'Other')", (t1, t2))
        conn.execute(
            "INSERT INTO app_users (id, tenant_id, email, role) VALUES "
            "(%s,%s,'lawyer@acme','responsible_lawyer'), (%s,%s,'outsider@acme','reviewer'), "
            "(%s,%s,'hr@acme','requester'), (%s,%s,'lawyer@other','responsible_lawyer')",
            (lawyer, t1, outsider, t1, requester, t1, other, t2),
        )
        for mid, tid in ((matter, t1), (other_matter, t2)):
            conn.execute(
                "INSERT INTO matters (id, tenant_id, title, type, risk_level, status, record) "
                "VALUES (%s,%s,'NDA','nda','LOW','open','{}')",
                (mid, tid),
            )
        conn.execute(
            "INSERT INTO matter_acl VALUES (%s,%s), (%s,%s)", (matter, lawyer, other_matter, other)
        )
        # matter document, tenant-wide policy, privileged tenant-wide memo
        docs = [(uuid4(), matter, False), (uuid4(), None, False), (uuid4(), None, True)]
        for did, mid, priv in docs:
            conn.execute(
                "INSERT INTO documents (id, tenant_id, matter_id, title, doc_type, privileged, "
                "sha256) VALUES (%s,%s,%s,'d','contract',%s,'x')",
                (did, t1, mid, priv),
            )
            conn.execute(
                "INSERT INTO chunks (tenant_id, document_id, heading_path, content) "
                "VALUES (%s,%s,'h','text')",
                (t1, did),
            )
        yield World(conn, t1, t2, lawyer, outsider, requester, matter)
        conn.close()
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(name))
            )


def count(conn: psycopg.Connection, table: str) -> int:
    row = conn.execute(sql.SQL("SELECT count(*) FROM {}").format(sql.Identifier(table))).fetchone()
    assert row is not None
    return int(row[0])


def test_user_on_acl_sees_matter_and_its_chunks(world: World) -> None:
    with user_scope(world.conn, world.tenant, world.lawyer):
        assert count(world.conn, "matters") == 1
        assert count(world.conn, "chunks") == 3  # matter doc + policy + privileged memo


def test_restricted_user_gets_nothing_from_the_matter(world: World) -> None:
    with user_scope(world.conn, world.tenant, world.outsider):
        assert count(world.conn, "matters") == 0
        assert count(world.conn, "matter_acl") == 0
        assert count(world.conn, "chunks") == 2  # tenant-wide only, matter doc hidden


def test_non_legal_role_cannot_see_privileged(world: World) -> None:
    with user_scope(world.conn, world.tenant, world.requester):
        assert count(world.conn, "chunks") == 1  # policy only


def test_no_scope_sees_nothing(world: World) -> None:
    with world.conn.transaction():
        world.conn.execute("SET LOCAL ROLE counsel_app")
        assert count(world.conn, "matters") == 0
        assert count(world.conn, "chunks") == 0


def test_pipeline_sees_whole_tenant_but_not_other_tenant(world: World) -> None:
    with pipeline_scope(world.conn, world.tenant):
        assert count(world.conn, "matters") == 1
        assert count(world.conn, "chunks") == 3
    with pipeline_scope(world.conn, world.other_tenant):
        assert count(world.conn, "chunks") == 0


def test_cannot_write_into_another_tenant(world: World) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with pipeline_scope(world.conn, world.tenant):
            world.conn.execute(
                "INSERT INTO matters (tenant_id, title, type, risk_level, status, record) "
                "VALUES (%s,'x','nda','LOW','open','{}')",
                (world.other_tenant,),
            )


def test_audit_log_is_append_only(world: World) -> None:
    with user_scope(world.conn, world.tenant, world.lawyer):
        event_id = write_event(
            world.conn,
            tenant_id=world.tenant,
            actor="test",
            action="viewed",
            matter_id=world.matter,
        )
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with user_scope(world.conn, world.tenant, world.lawyer):
            world.conn.execute("DELETE FROM audit_events WHERE id = %s", (event_id,))
    # even the owner cannot rewrite history
    with pytest.raises(psycopg.errors.RaiseException), world.conn.transaction():
        world.conn.execute("UPDATE audit_events SET action = 'edited' WHERE id = %s", (event_id,))
