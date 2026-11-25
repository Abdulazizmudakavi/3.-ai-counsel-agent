# AI Corporate Counsel Agent — prototype

Reads a legal mailbox, triages each email, drafts cited replies for NDA and internal policy
questions, and shows them in a review console. **Sending is hard-disabled** for the whole
prototype (`src/counsel/policy/sender.py`).

## Layout

| Path | Owner | What |
|---|---|---|
| `src/counsel/contracts/` | all three | The 3 shared records (Pydantic, strict). Only interface between stages |
| `contracts/*.schema.json` | generated | JSON Schemas exported from the models; CI fails if stale |
| `src/counsel/ingest, triage, matters`, `evals/` | Sana | Intake, triage, matters, test sets |
| `src/counsel/kb, agent, verify` | Arina | Knowledge, orchestrator, verifier |
| `src/counsel/gateway, policy, audit, api`, `console/`, `db/`, `infra/`, `.github/` | Abdul | Platform, controls, console |

## Local setup (Windows)

Needs: Git, Docker Desktop, [uv](https://docs.astral.sh/uv/) (installs Python 3.12 for you).

```powershell
winget install --id astral-sh.uv
uv python install 3.12
uv sync
Copy-Item .env.example .env
docker compose up -d db
uv run python scripts/migrate.py
uv run pytest
uv run uvicorn counsel.api.main:app --reload   # http://localhost:8000/health
```

### Try the stub email flow

Open http://localhost:8000/docs. Stub stages (gateway, triage, agent) are canned rules held in
memory, so every route can be exercised before the real stages land.

1. `GET /stub/users` gives the demo reviewer IDs.
2. `POST /stub/samples/{name}` runs a ready-made email: `nda_external`,
   `policy_question_internal`, `show_cause_hindi`, `legal_threat_customer`, `invoice_query`,
   `newsletter`, `prompt_injection`. Or `POST /stub/emails` with your own email.
3. `GET /stub/review-queue`, then `POST /stub/items/{item_id}/decision` with
   `{"reviewer_id": "...", "action": "approve" | "edit" | "reject" | "escalate"}`.
   Approve issues a token bound to the draft hash; sending stays disabled.
4. `GET /stub/matters`, `GET /stub/audit` to see the matter and every step logged.
   `POST /stub/reset` clears everything.

After changing a record in `src/counsel/contracts/`:

```powershell
uv run python scripts/export_schemas.py
```

## Rules built into the code

- Records reject unknown fields and wrong types; cross-field rules are enforced
  (legal email needs a category, an escalation-rule hit forces CRITICAL, CRITICAL gets no draft
  reply, every claim needs a verifier result, risk points must add up, draft hash must match).
- Row-level security: the console and agent run as `counsel_app` scoped to one user; they see
  only matters on that user's access list, and privileged documents only with a legal role.
  Ingestion runs as `counsel_pipeline`, scoped to one tenant. See `db/migrations/001_init.sql`.
- `audit_events` is append-only: no UPDATE/DELETE grant, and a trigger blocks even the owner.
- The login user the app connects with must be granted membership of both roles
  (`GRANT counsel_app, counsel_pipeline TO <login user>`), and must not be a superuser in AWS.

## Abdul — week 1 checklist

- [x] Repository with the blueprint layout, CI, PR template, CODEOWNERS (fill in usernames)
- [x] Draft the 3 record formats as code (review with Sana and Arina, then freeze at G1)
- [x] Postgres schema with row-level security + test that a restricted user gets nothing
- [ ] Create the GitHub repo, push, protect `main` (1 review, code owners, CI required)
- [ ] AWS account in Mumbai, Bedrock India access request — see `infra/README.md`
- [ ] Secrets manager; no keys in code or logs

## Decisions

- **Client isolation: `tenant_id` column + row-level security, not one schema per client**
  (decided by Abdul, 25 Nov 2026). The prototype has a single client, RLS is simpler to migrate
  and already passes the isolation tests in `tests/test_db_security.py`. Revisit before
  multi-client SaaS (Phase 3), where per-client schemas or databases may be required by clients.
