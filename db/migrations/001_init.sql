-- 001_init: core tables, row-level security, append-only audit log.
-- Two runtime roles, neither owns the tables, so RLS always applies to them:
--   counsel_app       console and agent retrieval; acts AS the requesting user (app.user_id)
--   counsel_pipeline  ingestion and triage; whole tenant (app.tenant_id), never another tenant

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'counsel_app') THEN
        CREATE ROLE counsel_app NOLOGIN NOBYPASSRLS;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'counsel_pipeline') THEN
        CREATE ROLE counsel_pipeline NOLOGIN NOBYPASSRLS;
    END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS app;

CREATE FUNCTION app.current_tenant_id() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$ SELECT nullif(current_setting('app.tenant_id', true), '')::uuid $$;

CREATE FUNCTION app.current_user_id() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$ SELECT nullif(current_setting('app.user_id', true), '')::uuid $$;

-- ---------------------------------------------------------------- tables

CREATE TABLE tenants (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_users (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants(id),
    email       text NOT NULL,
    role        text NOT NULL CHECK (role IN
                    ('requester', 'reviewer', 'responsible_lawyer', 'legal_admin', 'auditor')),
    UNIQUE (tenant_id, email)
);

CREATE TABLE matters (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   uuid NOT NULL REFERENCES tenants(id),
    title       text NOT NULL,
    type        text NOT NULL,
    states      text[] NOT NULL DEFAULT '{}',
    risk_level  text NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status      text NOT NULL CHECK (status IN
                    ('open', 'awaiting_counterparty', 'awaiting_internal', 'escalated', 'closed')),
    legal_hold  boolean NOT NULL DEFAULT false,
    record      jsonb NOT NULL,            -- full MatterRecord, validated in code
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE matter_acl (
    matter_id   uuid NOT NULL REFERENCES matters(id) ON DELETE CASCADE,
    user_id     uuid NOT NULL REFERENCES app_users(id),
    PRIMARY KEY (matter_id, user_id)
);

-- matter_id NULL = knowledge-base document (playbook, policy, statute) visible tenant-wide,
-- unless privileged, in which case legal roles only.
CREATE TABLE documents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id),
    matter_id       uuid REFERENCES matters(id),
    title           text NOT NULL,
    doc_type        text NOT NULL,
    version         integer NOT NULL DEFAULT 1,
    status          text NOT NULL DEFAULT 'executed'
                        CHECK (status IN ('draft', 'executed', 'superseded', 'in_force')),
    privileged      boolean NOT NULL DEFAULT false,
    sha256          text NOT NULL,
    effective_from  date,
    effective_to    date,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE chunks (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       uuid NOT NULL REFERENCES tenants(id),
    document_id     uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    heading_path    text NOT NULL,                 -- "MSA > 9 Liability > 9.2"
    content         text NOT NULL,
    language        text NOT NULL DEFAULT 'en',
    embedding       vector(1024),                  -- dimension fixed when the embedding model is chosen
    tsv             tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED
);
CREATE INDEX chunks_tsv_idx ON chunks USING gin (tsv);
CREATE INDEX chunks_doc_idx ON chunks (document_id);

CREATE TABLE audit_events (
    id          bigserial PRIMARY KEY,
    tenant_id   uuid NOT NULL REFERENCES tenants(id),
    occurred_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    actor       text NOT NULL,
    action      text NOT NULL,
    matter_id   uuid,
    payload     jsonb NOT NULL DEFAULT '{}'
);

-- ---------------------------------------------------------------- visibility helpers
-- SECURITY DEFINER so the ACL lookup itself is not filtered by RLS (no recursion).
-- Inside a SECURITY DEFINER function current_user is the owner, so the pipeline check
-- lives in app.is_pipeline() and is only called from invoker contexts (policies).

CREATE FUNCTION app.is_pipeline() RETURNS boolean
    LANGUAGE sql STABLE
    AS $$ SELECT current_user = 'counsel_pipeline' $$;

CREATE FUNCTION app.can_see_matter(m uuid) RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
    AS $$
        SELECT EXISTS (SELECT 1 FROM matter_acl a
                       WHERE a.matter_id = m AND a.user_id = app.current_user_id())
    $$;

CREATE FUNCTION app.is_legal_role() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public
    AS $$
        SELECT EXISTS (SELECT 1 FROM app_users u
                       WHERE u.id = app.current_user_id()
                         AND u.role IN ('reviewer', 'responsible_lawyer', 'legal_admin'))
    $$;

CREATE FUNCTION app.can_see_document(d documents) RETURNS boolean
    LANGUAGE sql STABLE
    AS $$
        SELECT d.tenant_id = app.current_tenant_id()
           AND (app.is_pipeline() OR (
                   (NOT d.privileged OR app.is_legal_role())
               AND (d.matter_id IS NULL OR app.can_see_matter(d.matter_id))))
    $$;

-- ---------------------------------------------------------------- row-level security

ALTER TABLE tenants      ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_users    ENABLE ROW LEVEL SECURITY;
ALTER TABLE matters      ENABLE ROW LEVEL SECURITY;
ALTER TABLE matter_acl   ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents    ENABLE ROW LEVEL SECURITY;
ALTER TABLE chunks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_self ON tenants
    USING (id = app.current_tenant_id());

CREATE POLICY users_same_tenant ON app_users
    USING (tenant_id = app.current_tenant_id());

CREATE POLICY matters_visible ON matters
    USING (tenant_id = app.current_tenant_id() AND (app.is_pipeline() OR app.can_see_matter(id)))
    WITH CHECK (tenant_id = app.current_tenant_id());

CREATE POLICY acl_visible ON matter_acl
    USING (EXISTS (SELECT 1 FROM matters m WHERE m.id = matter_acl.matter_id));

CREATE POLICY documents_visible ON documents
    USING (app.can_see_document(documents))
    WITH CHECK (tenant_id = app.current_tenant_id());

CREATE POLICY chunks_visible ON chunks
    USING (tenant_id = app.current_tenant_id()
           AND EXISTS (SELECT 1 FROM documents d WHERE d.id = chunks.document_id))
    WITH CHECK (tenant_id = app.current_tenant_id());

CREATE POLICY audit_same_tenant ON audit_events
    USING (tenant_id = app.current_tenant_id())
    WITH CHECK (tenant_id = app.current_tenant_id());

-- ---------------------------------------------------------------- grants

GRANT USAGE ON SCHEMA app TO counsel_app, counsel_pipeline;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA app TO counsel_app, counsel_pipeline;

GRANT SELECT ON tenants, app_users, matters, matter_acl, documents, chunks
    TO counsel_app, counsel_pipeline;
GRANT INSERT, UPDATE ON matters, matter_acl, documents, chunks TO counsel_pipeline;
GRANT UPDATE (status, risk_level, record) ON matters TO counsel_app;

-- Audit: insert and read only. No UPDATE/DELETE grant for anyone.
GRANT SELECT, INSERT ON audit_events TO counsel_app, counsel_pipeline;
GRANT USAGE ON SEQUENCE audit_events_id_seq TO counsel_app, counsel_pipeline;

-- Belt and braces: even the table owner cannot rewrite history.
CREATE FUNCTION app.audit_is_append_only() RETURNS trigger
    LANGUAGE plpgsql
    AS $$ BEGIN RAISE EXCEPTION 'audit_events is append-only'; END $$;

CREATE TRIGGER audit_no_update BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION app.audit_is_append_only();
CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON audit_events
    FOR EACH STATEMENT EXECUTE FUNCTION app.audit_is_append_only();
